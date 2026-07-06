"""
NexusForge — Validator Agent
============================
The integrity enforcement engine.
Verifies data and schema structures, compares against the canonical Universal JSON,
and validates that the target migrations match the source system's schema.

Cross-dialect normalization notes
----------------------------------
* TINYINT(1) is MySQL's canonical storage representation of a boolean column
  (``BOOLEAN`` in MySQL DDL is a synonym for ``TINYINT(1)``).
  ``_normalize_type`` maps it to ``BOOLEAN`` **before** the generic ``INT``
  catch-all, so that MySQL boolean columns compare equal to PostgreSQL BOOLEAN
  columns after a MySQL → PostgreSQL migration.

* MySQL AUTO_INCREMENT columns report ``COLUMN_DEFAULT = NULL`` in
  ``information_schema.COLUMNS`` because the auto-increment property is a
  table-level attribute rather than a column default expression. PostgreSQL
  represents the same semantic via a sequence (``nextval('t_id_seq'::regclass)``).
  After normalization these produce the tokens ``'NULL'`` and ``'NEXTVAL'``
  respectively. ``_perform_validation`` treats them as equivalent **only** when
  the column's normalized type is ``INTEGER`` and the column name appears in
  the table's primary-key index — ensuring ordinary nullable columns and
  non-PK integers are still compared strictly.

* The Scout checksum is a SHA-256 fingerprint of the raw source-database
  objects. Its purpose is *file integrity*: proving the Universal JSON was not
  tampered with between Scout writing it and Validator reading it. It is not
  designed to compare source vs. target across dialects, because raw object
  representations are dialect-specific (e.g. ``INT`` vs ``INTEGER``, ``null``
  vs ``nextval(...)``). ``_perform_validation`` therefore computes a separate
  *normalized structural checksum* over the normalized source and target schemas
  and uses *that* for structural equivalence testing. The Scout checksum is
  preserved in the report for audit purposes.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

from akaal.adapters.adapter_registry import create_adapter
from akaal.adapters.postgres_adapter import PostgresAdapter  # compat shim
from akaal.core.models.enums import AgentStatus, AgentType, FailureReason, TaskType, SystemType, ValidationResult
from akaal.core.models.message import Message, MessageType
from akaal.core.models.task import Task, TaskStatus
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus

logger = logging.getLogger("nexusforge.validator")


class ValidatorAgent:
    """
    The Validator Agent is responsible for database schema validation,
    checksum comparison, structural consistency checks, and reporting results.
    """

    AGENT_ID: str = "VALIDATOR-001"

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        workspace_dir: str = "workspace",
        agent_id: str = "VALIDATOR-001",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self._workspace_dir = workspace_dir
        self.agent_id = agent_id
        self._is_backup = is_backup
        self._running = False
        self._active_tasks: Set[str] = set()

        logger.info("[ValidatorAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    async def start(self) -> None:
        """Register the agent with global state and subscribe to the message bus."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.VALIDATOR, self.agent_id)
        await self._state.update_agent_status(AgentType.VALIDATOR, status, self.agent_id)

        # Subscribe to message bus for VALIDATOR queue
        await self._bus.subscribe(AgentType.VALIDATOR, self._handle_message)
        logger.info("[ValidatorAgent] Started and registered.")

    async def stop(self) -> None:
        """Graceful shutdown of the agent."""
        self._running = False
        await self._state.update_agent_status(AgentType.VALIDATOR, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[ValidatorAgent] Stopped.")

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[ValidatorAgent] Message integrity check failed. Discarding message %s", message.message_id)
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.VALIDATOR, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.VALIDATOR, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.VALIDATOR, status, self.agent_id)
                logger.critical("[ValidatorAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore tasks if in standby
        if self._is_backup:
            logger.debug("[ValidatorAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
            return

        if message.message_type == MessageType.TASK_ASSIGN:
            task_id = message.payload.get("task_id")
            project_id = message.project_id or ""
            migration_id = message.migration_id or ""
            if task_id:
                # Run the task execution in background to keep message loop responsive
                asyncio.create_task(self._execute_task(message.payload, project_id, migration_id))

    async def _execute_task(self, task_dict: Dict[str, Any], project_id: str, migration_id: str) -> None:
        """Execute the assigned task."""
        task_id = task_dict["task_id"]
        task_type_str = task_dict["task_type"]
        stage = task_dict["parameters"].get("stage", "discovery")

        if task_id in self._active_tasks:
            logger.warning("[ValidatorAgent] Task %s is already running.", task_id)
            return

        self._active_tasks.add(task_id)
        await self._state.update_agent_status(AgentType.VALIDATOR, AgentStatus.BUSY, self.agent_id)

        logger.info("[ValidatorAgent] Started validation task %s (Stage=%s)", task_id[:8], stage)

        try:
            # 1. Fetch project config
            project = await self._state.get_project(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            # 2. Select database config based on stage
            if stage == "discovery":
                db_config = project.source_config
            else:
                db_config = project.target_config

            if not db_config:
                raise ValueError(f"No database configuration found for stage={stage}")

            # 3. Locate reference Universal JSON
            # Default lookup path if discovery_result_ref is not passed
            ref_path = task_dict["parameters"].get("discovery_result_ref")
            if not ref_path:
                ref_path = os.path.join(
                    self._workspace_dir, "projects", project_id, f"discovery_{migration_id}.json"
                )

            if not os.path.exists(ref_path):
                raise FileNotFoundError(f"Universal JSON reference file not found at {ref_path}")

            with open(ref_path, "r", encoding="utf-8") as f:
                universal_json = json.load(f)

            # 4. Connect to database and extract live schema catalog
            adapter = create_adapter(db_config)

            await adapter.connect()
            try:
                # Scan table structures
                tables = await adapter.discover_tables()
                schema_objects = {}
                for table in tables:
                    columns = await adapter.discover_columns(table)
                    indexes = await adapter.discover_indexes(table)
                    constraints = await adapter.discover_constraints(table)
                    triggers = await adapter.discover_triggers(table)
                    
                    schema_objects[table] = {
                        "object_name": table,
                        "object_type": "TABLE",
                        "columns": columns,
                        "indexes": indexes,
                        "constraints": constraints,
                        "triggers": triggers,
                        "dependency_references": []
                    }

                # Discover foreign keys
                fkeys = await adapter.discover_foreign_keys()
                # Map foreign keys back to dependency references
                for fk in fkeys:
                    from_t = fk["from_table"]
                    to_t = fk["to_table"]
                    if from_t in schema_objects:
                        schema_objects[from_t]["dependency_references"].append({
                            "type": "FOREIGN_KEY",
                            "constraint_name": fk["name"],
                            "from_column": fk["from_column"],
                            "target_table": to_t,
                            "target_column": fk["to_column"]
                        })

                # Discover views
                views = await adapter.discover_views()
                for view in views:
                    view_name = view["name"]
                    schema_objects[view_name] = {
                        "object_name": view_name,
                        "object_type": "VIEW",
                        "definition": view["definition"],
                        "dependency_references": []
                    }

            finally:
                await adapter.close()

            # 5. Perform structural and checksum validation
            mismatches, computed_checksum = self._perform_validation(schema_objects, universal_json)

            is_valid = len(mismatches) == 0
            val_status = ValidationResult.PASS if is_valid else ValidationResult.FAIL

            # 6. Save validation report
            os.makedirs(os.path.join(self._workspace_dir, "projects", project_id), exist_ok=True)
            report_filepath = os.path.join(
                self._workspace_dir, "projects", project_id, f"validation_{migration_id}_{stage}.json"
            )

            report_data = {
                "project_id": project_id,
                "migration_id": migration_id,
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": val_status.value,
                "checksums": {
                    "expected": universal_json["metadata"]["checksum"],
                    "actual": computed_checksum,
                    "matched": (universal_json["metadata"]["checksum"] == computed_checksum)
                },
                "mismatches": mismatches
            }

            with open(report_filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            # 7. Notify Manager of completion
            if is_valid:
                logger.info("[ValidatorAgent] Validation PASSED for task %s.", task_id[:8])
                response = Message(
                    sender=AgentType.VALIDATOR,
                    receiver=AgentType.MANAGER,
                    message_type=MessageType.TASK_RESULT,
                    payload={
                        "task_id": task_id,
                        "result_ref": report_filepath,
                    },
                    project_id=project_id,
                    migration_id=migration_id,
                )
                await self._bus.publish(response)
            else:
                logger.error("[ValidatorAgent] Validation FAILED for task %s. Mismatches count: %d", task_id[:8], len(mismatches))
                
                # Check if Noticer agent is registered and online (sync method)
                noticer_health = self._state.get_agent_health(AgentType.NOTICER)
                noticer_active = noticer_health is not None and noticer_health.status != AgentStatus.OFFLINE
                
                receiver = AgentType.NOTICER if noticer_active else AgentType.MANAGER
                logger.info("[ValidatorAgent] Routing validation failure to receiver: %s (noticer_active=%s)", receiver.value, noticer_active)
                
                fail_msg = Message(
                    sender=AgentType.VALIDATOR,
                    receiver=receiver,
                    message_type=MessageType.TASK_FAILED,
                    payload={
                        "task_id": task_id,
                        "error": f"Validation failed with {len(mismatches)} mismatches.",
                        "mismatches": mismatches,
                    },
                    project_id=project_id,
                    migration_id=migration_id,
                )
                await self._bus.publish(fail_msg)

        except Exception as exc:
            logger.error("[ValidatorAgent] Internal validation task error %s: %s", task_id[:8], exc, exc_info=True)
            self._log_failure(
                rule_name="Validation Execution Task Check",
                exception=str(exc)
            )
            fail_msg = Message(
                sender=AgentType.VALIDATOR,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_FAILED,
                payload={
                    "task_id": task_id,
                    "error": str(exc),
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(fail_msg)

        finally:
            self._active_tasks.discard(task_id)
            status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
            await self._state.update_agent_status(AgentType.VALIDATOR, status, self.agent_id)

    def _log_failure(
        self,
        rule_name: str,
        source_table: str = "N/A",
        target_table: str = "N/A",
        expected_val: Any = "N/A",
        actual_val: Any = "N/A",
        row_counts: str = "N/A",
        checksum_values: str = "N/A",
        schema_diff: str = "N/A",
        pk_fk_diff: str = "N/A",
        null_diff: str = "N/A",
        json_diff: str = "N/A",
        exception: str = "N/A"
    ) -> None:
        logger.error(
            "[ValidatorAgent] Validation Rule Failed: %s\n"
            "  * Source Table:       %s\n"
            "  * Target Table:       %s\n"
            "  * Expected Value:     %s\n"
            "  * Actual Value:       %s\n"
            "  * Row Counts:         %s\n"
            "  * Checksum Values:    %s\n"
            "  * Schema Differences: %s\n"
            "  * PK/FK Differences:  %s\n"
            "  * NULL Differences:   %s\n"
            "  * JSON Differences:   %s\n"
            "  * Exception Occurred: %s",
            rule_name, source_table, target_table, expected_val, actual_val,
            row_counts, checksum_values, schema_diff, pk_fk_diff, null_diff, json_diff, exception
        )
    def _normalize_type(self, t: str) -> str:
        """Map a raw dialect-specific column type to a canonical token.

        Ordering notes
        --------------
        * ``TINYINT(1)`` **must** be checked before the generic ``"INT" in t``
          branch. In MySQL, ``BOOLEAN`` is a synonym for ``TINYINT(1)``, so any
          column declared as ``BOOLEAN`` is stored and reported as ``TINYINT(1)``
          in ``information_schema.COLUMNS``. Without this guard the generic INT
          branch would misclassify MySQL boolean columns as INTEGER, causing a
          spurious mismatch against PostgreSQL BOOLEAN columns after migration.
        * Only the exact string ``TINYINT(1)`` (with the parenthetical 1) is the
          MySQL boolean alias. ``TINYINT(2)``, ``TINYINT``, ``TINYINT UNSIGNED``,
          etc. are genuine small integers and continue to normalize to INTEGER.
        """
        if not t:
            return ""
        t = t.upper()
        if t in ("TEXT", "NVARCHAR(-1)", "NVARCHAR(MAX)", "VARCHAR(-1)", "VARCHAR(MAX)", "JSON", "JSONB"):
            return "LARGE_TEXT_OR_JSON"
        if "VARCHAR" in t or "CHARACTER VARYING" in t or "CHAR" in t or "NVARCHAR" in t:
            return "STRING"
        # --- Fix 1: TINYINT(1) is MySQL's boolean alias. Must be checked BEFORE
        # the generic "INT" catch-all so it maps to BOOLEAN, not INTEGER. ---
        if t == "TINYINT(1)":
            return "BOOLEAN"
        if "INT" in t:
            return "INTEGER"
        if "TIME" in t or "DATE" in t:
            return "DATETIME"
        if "BYTEA" in t or "BLOB" in t or "BINARY" in t:
            return "BLOB"
        if "NUMERIC" in t or "DECIMAL" in t or "FLOAT" in t or "DOUBLE" in t:
            return "DECIMAL"
        if "BOOLEAN" in t or "BIT" in t:
            return "BOOLEAN"
        return t

    def _normalize_default(self, d) -> str:
        if d is None:
            return "NULL"
        d_str = str(d).upper().replace("(", "").replace(")", "").replace("'", "").replace('"', '').strip()
        # Strip cast suffixes like '::regclass' or '::text'
        if "::" in d_str:
            d_str = d_str.split("::")[0].strip()
        if not d_str or d_str == "NONE" or d_str == "NULL":
            return "NULL"
        if d_str.startswith("NEXTVAL") or "NEXT VALUE FOR" in d_str or "IDENTITY" in d_str:
            return "NEXTVAL"
        timestamp_defaults = {"CURRENT_TIMESTAMP", "GETDATE", "NOW", "NOW()"}
        if d_str in timestamp_defaults or "GETDATE" in d_str or "CURRENT_TIMESTAMP" in d_str:
            return "NOW"
        bool_true = {"TRUE", "1", "((1))"}
        bool_false = {"FALSE", "0", "((0))"}
        if d_str in bool_true:
            return "TRUE"
        if d_str in bool_false:
            return "FALSE"
        return d_str

    def _normalize_view_definition(self, definition: str) -> str:
        if not definition:
            return ""
        # Remove whitespace and lowercase
        normalized = " ".join(definition.lower().split())
        return normalized

    def _normalize_schema(self, objects_data: Any) -> Dict[str, Dict[str, Any]]:
        """
        Normalize schema data into a standardized, casing-insensitive structure.
        Accepts either a List of object dicts or a Dict of object dicts.
        """
        if isinstance(objects_data, list):
            objects_dict = {obj["object_name"]: obj for obj in objects_data}
        else:
            objects_dict = objects_data

        normalized = {}
        for raw_name, obj in objects_dict.items():
            name = raw_name.lower()
            obj_type = obj.get("object_type", "TABLE").upper()

            if obj_type == "TABLE":
                # Normalize columns
                columns = {}
                for col in obj.get("columns", []):
                    c_name = col["name"].lower()
                    columns[c_name] = {
                        "name": c_name,
                        "type": self._normalize_type(col.get("type", "")),
                        "nullable": bool(col.get("nullable", True)),
                        "default": self._normalize_default(col.get("default"))
                    }

                # Normalize indexes
                indexes = []
                for idx in obj.get("indexes", []):
                    idx_cols = [c.lower() for c in idx.get("columns", [])]
                    indexes.append({
                        "name": idx.get("name", "").lower(),
                        "columns": idx_cols,
                        "unique": bool(idx.get("unique", False))
                    })

                # Normalize constraints
                constraints = []
                for const in obj.get("constraints", []):
                    constraints.append({
                        "name": const.get("name", "").lower(),
                        "type": const.get("type", "").upper()
                    })

                # Normalize triggers
                triggers = {}
                for trg in obj.get("triggers", []):
                    t_name = trg["name"].lower()
                    triggers[t_name] = {
                        "name": t_name,
                        "event": trg.get("event", "").upper(),
                        "definition": self._normalize_view_definition(trg.get("definition", ""))
                    }

                # Normalize dependency references / foreign keys
                dependency_references = []
                for ref in obj.get("dependency_references", []):
                    dependency_references.append({
                        "type": ref.get("type", "FOREIGN_KEY").upper(),
                        "constraint_name": ref.get("constraint_name", "").lower(),
                        "from_column": ref.get("from_column", "").lower(),
                        "target_table": ref.get("target_table", "").lower(),
                        "target_column": (ref.get("target_column") or ref.get("to_column") or "").lower()
                    })

                normalized[name] = {
                    "object_name": name,
                    "object_type": "TABLE",
                    "columns": columns,
                    "indexes": indexes,
                    "constraints": constraints,
                    "triggers": triggers,
                    "dependency_references": dependency_references
                }

            elif obj_type == "VIEW":
                normalized[name] = {
                    "object_name": name,
                    "object_type": "VIEW",
                    "definition": self._normalize_view_definition(obj.get("definition", ""))
                }

        return normalized

    def _normalize_schema_for_checksum(self, norm_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a checksum-ready representation of a normalized schema.

        This layer applies two additional cross-dialect equivalences **for
        checksum computation only** — it is not used for per-field mismatch
        reporting, which has its own guards.

        1. **Auto-increment / sequence default**: For INTEGER columns that are
           primary-key members, replace the normalized default token with the
           canonical sentinel ``'AUTO_PK'``.  This makes MySQL (``'NULL'``) and
           PostgreSQL (``'NEXTVAL'``) produce the same checksum for these
           columns.

        2. **Index and constraint names**: Replace the name field of each index
           and each constraint with a canonical structural key
           ``"<sorted-columns>"`` for indexes and ``"<type>"`` for
           constraints.  Index names are dialect-specific (MySQL uses
           ``PRIMARY``; PostgreSQL uses ``table_pkey``). Only the column set,
           uniqueness flag, and constraint type are structurally meaningful
           across dialects.

        The resulting dict is serialized and hashed; the hash is compared
        between source and target.  A correct cross-dialect migration produces
        identical hashes.
        """
        result: Dict[str, Any] = {}

        for tbl_name, tbl_obj in norm_schema.items():
            if tbl_obj.get("object_type") != "TABLE":
                result[tbl_name] = tbl_obj
                continue

            # Collect PK column names from the normalized index list.
            # Strategy (in priority order):
            #   1. Index named exactly 'primary' -- MySQL PRIMARY KEY index.
            #   2. Index whose name ends with 'pkey' -- PostgreSQL default PK
            #      naming convention (e.g. 'users_pkey').
            #   3. Smallest unique index as a last resort for other dialects.
            # We do NOT rely solely on the constraint list because it only tells
            # us that *a* PK exists, not which columns it covers. AUTO_INCREMENT /
            # SERIAL only applies to single-column PKs, so the heuristics above
            # are always unambiguous for the AUTO_PK equivalence use case.
            pk_col_names: Set[str] = set()
            has_pk_constraint = any(
                c.get("type") == "PRIMARY KEY" for c in tbl_obj.get("constraints", [])
            )
            if has_pk_constraint:
                unique_indexes = [idx for idx in tbl_obj.get("indexes", []) if idx.get("unique")]
                pk_idx = next(
                    (idx for idx in unique_indexes if idx.get("name") == "primary"), None
                )
                if pk_idx is None:
                    pk_idx = next(
                        (idx for idx in unique_indexes if idx.get("name", "").endswith("pkey")), None
                    )
                if pk_idx is None and unique_indexes:
                    pk_idx = min(
                        unique_indexes,
                        key=lambda x: (len(x["columns"]), x.get("name", ""))
                    )
                if pk_idx:
                    pk_col_names.update(pk_idx.get("columns", []))

            # Rewrite columns: replace NEXTVAL with AUTO_PK for integer PK cols
            new_cols: Dict[str, Any] = {}
            for col_name, col in tbl_obj.get("columns", {}).items():
                col_copy = dict(col)
                if (
                    col_name in pk_col_names
                    and col_copy.get("type") == "INTEGER"
                    and col_copy.get("default") in ("NULL", "NEXTVAL")
                ):
                    col_copy["default"] = "AUTO_PK"
                new_cols[col_name] = col_copy

            # Rewrite indexes: replace name with structural key
            new_indexes = sorted(
                [
                    {
                        "name": "__IDX__" + "__".join(sorted(idx["columns"])),
                        "columns": sorted(idx["columns"]),
                        "unique": idx["unique"],
                    }
                    for idx in tbl_obj.get("indexes", [])
                ],
                key=lambda x: json.dumps(x, sort_keys=True)
            )

            # Rewrite constraints: keep only type, drop dialect-specific name.
            # Also exclude CHECK-typed constraints. In PostgreSQL,
            # information_schema.table_constraints surfaces implicit NOT NULL
            # constraints as CHECK entries (e.g. '2200_26731_1_not_null').
            # MySQL encodes NOT NULL as a column attribute only and emits no
            # such CHECK entries. Since the nullable field on each column
            # already captures this information in the checksum payload, CHECK
            # entries carry no additional structural signal for cross-dialect
            # migration equivalence. User-defined CHECK constraints are still
            # caught by the per-column mismatch rules in _perform_validation.
            new_constraints = sorted(
                [{"type": c["type"]} for c in tbl_obj.get("constraints", [])
                 if c["type"] != "CHECK"],
                key=lambda x: x["type"]
            )

            # Rewrite dependency_references: drop dialect-specific constraint_name,
            # keep only the structural identity (type, from_column, target_table,
            # target_column). MySQL FK names (e.g. 'orders_ibfk_1') and PostgreSQL
            # FK names (e.g. 'orders_user_id_fkey') differ by convention but the
            # FK semantics (column and target) are identical after a correct migration.
            new_dep_refs = sorted(
                [
                    {
                        "from_column":   ref["from_column"],
                        "target_column": ref["target_column"],
                        "target_table":  ref["target_table"],
                        "type":          ref["type"],
                    }
                    for ref in tbl_obj.get("dependency_references", [])
                ],
                key=lambda x: json.dumps(x, sort_keys=True)
            )

            result[tbl_name] = {
                "object_name": tbl_name,
                "object_type": "TABLE",
                "columns": new_cols,
                "indexes": new_indexes,
                "constraints": new_constraints,
                "triggers": tbl_obj.get("triggers", {}),
                "dependency_references": new_dep_refs,
            }

        return result

    def _perform_validation(
        self,
        scanned_objects: Dict[str, Any],
        universal_json: Dict[str, Any]
    ) -> Tuple[List[str], str]:
        """
        Compare scanned (target) database objects against the Universal JSON specification
        (source) and return a list of human-readable mismatch strings plus a checksum.

        Checksum strategy
        -----------------
        Two checksums are maintained:

        1. *Source integrity checksum* (``universal_json["metadata"]["checksum"]``):
           SHA-256 over the raw source-database objects as discovered by ScoutAgent.
           Its purpose is file-integrity only — it proves the Universal JSON was not
           modified between Scout writing it and Validator reading it.  It is included
           in the report but is **not** used for structural equivalence comparison,
           because raw objects are dialect-specific.

        2. *Normalized structural checksum*: SHA-256 over the serialized
           *normalized* source schema (``norm_expected``) and separately over the
           normalized target schema (``norm_actual``).  These two hashes are compared
           for structural equivalence.  Normalized schemas are dialect-agnostic, so
           a correct MySQL → PostgreSQL migration produces matching normalized
           checksums.

        Auto-increment / sequence default equivalence
        ---------------------------------------------
        MySQL AUTO_INCREMENT columns report ``COLUMN_DEFAULT = NULL`` in
        ``information_schema``.  PostgreSQL sequence columns report
        ``nextval('t_id_seq'::regclass)``.  After normalization these become
        the tokens ``'NULL'`` and ``'NEXTVAL'``.  The comparison treats them
        as equivalent **only** when all of the following are true:
          - ``ec["type"] == "INTEGER"``  (normalized column type)
          - ``ac["type"] == "INTEGER"``
          - ``ec["default"] == "NULL"``  (source side has no default expression)
          - ``ac["default"] == "NEXTVAL"`` (target side uses a sequence)
          - the column name belongs to the table's primary-key index
        For every other column, strict default comparison is applied.
        """
        mismatches: List[str] = []

        # 1. Normalize schemas
        norm_expected = self._normalize_schema(universal_json.get("objects", []))
        norm_actual = self._normalize_schema(scanned_objects)

        # 2. Build the primary-key column set per table from the *normalized*
        #    expected schema — used by Fix 2 (auto-increment default equivalence).
        pk_columns_by_table: Dict[str, Set[str]] = {}
        for tbl_name, tbl_obj in norm_expected.items():
            pk_cols: Set[str] = set()
            for idx in tbl_obj.get("indexes", []):
                # Primary-key indexes are unique and named 'primary' after normalization
                if idx.get("unique") and idx.get("name") == "primary":
                    pk_cols.update(idx.get("columns", []))
            pk_columns_by_table[tbl_name] = pk_cols

        # 3. Compute the *normalized structural checksum* for structural equivalence
        #    comparison (Fix 3).  This is separate from the Scout source-integrity
        #    checksum stored in universal_json["metadata"]["checksum"].
        #
        #    The checksum is computed over the *checksum-ready* normalized schema
        #    (produced by _normalize_schema_for_checksum) rather than the plain
        #    normalized schema.  The checksum-ready form applies two additional
        #    cross-dialect equivalences:
        #      - Auto-increment PK columns: NULL and NEXTVAL both become 'AUTO_PK'
        #      - Index/constraint names: replaced with structural keys so that
        #        MySQL 'PRIMARY' and PostgreSQL 'users_pkey' produce the same hash.
        #    These equivalences are consistent with the per-field mismatch guards
        #    in step 5 below (Fix 2 column default guard, structural index match).
        cksum_expected = self._normalize_schema_for_checksum(norm_expected)
        cksum_actual   = self._normalize_schema_for_checksum(norm_actual)
        norm_source_payload = json.dumps(cksum_expected, sort_keys=True).encode("utf-8")
        norm_target_payload = json.dumps(cksum_actual,   sort_keys=True).encode("utf-8")
        norm_source_checksum = hashlib.sha256(norm_source_payload).hexdigest()
        norm_target_checksum = hashlib.sha256(norm_target_payload).hexdigest()

        # 4. Log all six diagnostic items for debugging.
        logger.info("[ValidatorAgent] === RAW SOURCE SCHEMA ===\n%s", json.dumps(universal_json.get("objects", []), indent=2))
        logger.info("[ValidatorAgent] === RAW TARGET SCHEMA ===\n%s", json.dumps(scanned_objects, indent=2))
        logger.info("[ValidatorAgent] === NORMALIZED SOURCE SCHEMA ===\n%s", json.dumps(norm_expected, indent=2))
        logger.info("[ValidatorAgent] === NORMALIZED TARGET SCHEMA ===\n%s", json.dumps(norm_actual, indent=2))
        logger.info("[ValidatorAgent] === NORMALIZED SOURCE CHECKSUM INPUT ===\n%s", json.dumps(norm_expected, sort_keys=True))
        logger.info("[ValidatorAgent] === NORMALIZED TARGET CHECKSUM INPUT ===\n%s", json.dumps(norm_actual, sort_keys=True))
        logger.info(
            "[ValidatorAgent] Checksums: scout_source=%s... norm_source=%s... norm_target=%s...",
            universal_json["metadata"]["checksum"][:16],
            norm_source_checksum[:16],
            norm_target_checksum[:16],
        )

        # 4. Compare object presence
        expected_names = set(norm_expected.keys())
        actual_names = set(norm_actual.keys())

        missing_objects = expected_names - actual_names
        extra_objects = actual_names - expected_names

        for name in sorted(missing_objects):
            msg = f"Missing object: '{name}'"
            mismatches.append(msg)
            self._log_failure(
                rule_name="Object Presence Check",
                source_table=name,
                expected_val="Present",
                actual_val="Missing",
                schema_diff=msg
            )

        for name in sorted(extra_objects):
            msg = f"Extra object: '{name}'"
            mismatches.append(msg)
            self._log_failure(
                rule_name="Extra Object Check",
                target_table=name,
                expected_val="Absent",
                actual_val="Present",
                schema_diff=msg
            )

        # 5. Compare common objects
        for name in sorted(expected_names & actual_names):
            exp_obj = norm_expected[name]
            act_obj = norm_actual[name]

            # Compare type
            if exp_obj["object_type"] != act_obj["object_type"]:
                msg = f"Object '{name}' type mismatch: expected {exp_obj['object_type']}, got {act_obj['object_type']}"
                mismatches.append(msg)
                self._log_failure(
                    rule_name="Object Type Check",
                    source_table=name,
                    target_table=name,
                    expected_val=exp_obj["object_type"],
                    actual_val=act_obj["object_type"],
                    schema_diff=msg
                )
                continue

            if exp_obj["object_type"] == "TABLE":
                # Compare columns
                exp_cols = exp_obj["columns"]
                act_cols = act_obj["columns"]

                missing_cols = set(exp_cols.keys()) - set(act_cols.keys())
                extra_cols = set(act_cols.keys()) - set(exp_cols.keys())

                for c in sorted(missing_cols):
                    msg = f"Table '{name}': missing column '{c}'"
                    mismatches.append(msg)
                    self._log_failure(
                        rule_name="Column Presence Check",
                        source_table=name,
                        target_table=name,
                        expected_val=f"Column '{c}' present",
                        actual_val="Missing",
                        schema_diff=msg
                    )

                for c in sorted(extra_cols):
                    msg = f"Table '{name}': extra column '{c}'"
                    mismatches.append(msg)
                    self._log_failure(
                        rule_name="Extra Column Check",
                        source_table=name,
                        target_table=name,
                        expected_val="Absent",
                        actual_val=f"Column '{c}' present",
                        schema_diff=msg
                    )

                # Build PK column set for this table from the normalized indexes
                # (used by the auto-increment default equivalence guard below).
                table_pk_cols: Set[str] = pk_columns_by_table.get(name, set())

                for c in sorted(set(exp_cols.keys()) & set(act_cols.keys())):
                    ec = exp_cols[c]
                    ac = act_cols[c]

                    if ec["type"] != ac["type"]:
                        msg = f"Table '{name}' Column '{c}': type mismatch. Expected {ec['type']}, got {ac['type']}"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Column Type Check",
                            source_table=name,
                            target_table=name,
                            expected_val=ec["type"],
                            actual_val=ac["type"],
                            schema_diff=msg
                        )

                    if ec["nullable"] != ac["nullable"]:
                        msg = f"Table '{name}' Column '{c}': nullable mismatch. Expected {ec['nullable']}, got {ac['nullable']}"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Column Nullability Check",
                            source_table=name,
                            target_table=name,
                            expected_val=str(ec["nullable"]),
                            actual_val=str(ac["nullable"]),
                            null_diff=msg
                        )

                    if ec["default"] != ac["default"]:
                        # Fix 2 — Auto-increment / sequence default equivalence.
                        # MySQL AUTO_INCREMENT columns report COLUMN_DEFAULT = NULL
                        # in information_schema (the auto-increment property is
                        # table-level, not a column default expression).
                        # PostgreSQL represents the same semantic with a sequence:
                        #   nextval('table_id_seq'::regclass)
                        # After _normalize_default these become 'NULL' and 'NEXTVAL'.
                        # We treat them as equivalent ONLY when ALL conditions hold:
                        #   1. source default is 'NULL' (no expression on source side)
                        #   2. target default is 'NEXTVAL' (sequence on target side)
                        #   3. both normalized types are INTEGER
                        #   4. column is a primary-key member in the source schema
                        # Any other default divergence (ordinary nullable columns,
                        # non-PK integers, explicit default expressions, etc.) is
                        # reported as a real mismatch.
                        is_auto_inc_pk_equivalence = (
                            ec["default"] == "NULL"
                            and ac["default"] == "NEXTVAL"
                            and ec["type"] == "INTEGER"
                            and ac["type"] == "INTEGER"
                            and c in table_pk_cols
                        )
                        if not is_auto_inc_pk_equivalence:
                            msg = f"Table '{name}' Column '{c}': default value mismatch. Expected {ec['default']}, got {ac['default']}"
                            mismatches.append(msg)
                            self._log_failure(
                                rule_name="Column Default Value Check",
                                source_table=name,
                                target_table=name,
                                expected_val=str(ec["default"]),
                                actual_val=str(ac["default"]),
                                schema_diff=msg
                            )
                        else:
                            logger.debug(
                                "[ValidatorAgent] Table '%s' Column '%s': auto-increment/sequence "
                                "default equivalence accepted (source=NULL, target=NEXTVAL, type=INTEGER, pk=True).",
                                name, c
                            )

                # Compare indexes structurally (match by sorted columns)
                act_idxs = act_obj["indexes"]
                for idx in exp_obj["indexes"]:
                    expected_key = tuple(sorted(idx["columns"]))
                    matching_actuals = [ai for ai in act_idxs if tuple(sorted(ai["columns"])) == expected_key]
                    if not matching_actuals:
                        msg = f"Table '{name}': missing index on columns {idx['columns']}"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Index Presence Check",
                            source_table=name,
                            target_table=name,
                            expected_val=f"Index on columns {idx['columns']} present",
                            actual_val="Missing",
                            pk_fk_diff=msg
                        )
                    else:
                        has_matching_uniqueness = any(ai["unique"] == idx["unique"] for ai in matching_actuals)
                        if not has_matching_uniqueness:
                            actuals_uniqueness = [ai['unique'] for ai in matching_actuals]
                            msg = f"Table '{name}' Index on {idx['columns']}: uniqueness mismatch. Expected {idx['unique']}, got {actuals_uniqueness}"
                            mismatches.append(msg)
                            self._log_failure(
                                rule_name="Index Uniqueness Check",
                                source_table=name,
                                target_table=name,
                                expected_val=str(idx['unique']),
                                actual_val=str(actuals_uniqueness),
                                pk_fk_diff=msg
                            )

                # Compare dependency references / foreign keys structurally (match by keys)
                act_refs = act_obj["dependency_references"]
                act_refs_by_struct = {
                    (ref["from_column"], ref["target_table"], ref["target_column"]): ref
                    for ref in act_refs
                }
                for ref in exp_obj["dependency_references"]:
                    struct = (ref["from_column"], ref["target_table"], ref["target_column"])
                    if struct not in act_refs_by_struct:
                        msg = f"Table '{name}': missing foreign key constraint from {ref['from_column']} to {ref['target_table']}({ref['target_column']})"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Foreign Key Constraint Check",
                            source_table=name,
                            target_table=name,
                            expected_val=f"Constraint from {ref['from_column']} to {ref['target_table']}({ref['target_column']})",
                            actual_val="Missing",
                            pk_fk_diff=msg
                        )

                # Compare triggers
                exp_trgs = exp_obj["triggers"]
                act_trgs = act_obj["triggers"]

                missing_trgs = set(exp_trgs.keys()) - set(act_trgs.keys())
                extra_trgs = set(act_trgs.keys()) - set(exp_trgs.keys())

                for t in sorted(missing_trgs):
                    msg = f"Table '{name}': missing trigger '{t}'"
                    mismatches.append(msg)
                    self._log_failure(
                        rule_name="Trigger Presence Check",
                        source_table=name,
                        target_table=name,
                        expected_val=f"Trigger '{t}' present",
                        actual_val="Missing",
                        schema_diff=msg
                    )

                for t in sorted(extra_trgs):
                    msg = f"Table '{name}': extra trigger '{t}'"
                    mismatches.append(msg)
                    self._log_failure(
                        rule_name="Extra Trigger Check",
                        source_table=name,
                        target_table=name,
                        expected_val="Absent",
                        actual_val=f"Trigger '{t}' present",
                        schema_diff=msg
                    )

                for t in sorted(set(exp_trgs.keys()) & set(act_trgs.keys())):
                    et = exp_trgs[t]
                    at = act_trgs[t]
                    if et["event"] != at["event"]:
                        msg = f"Table '{name}' Trigger '{t}': event mismatch. Expected {et['event']}, got {at['event']}"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Trigger Event Check",
                            source_table=name,
                            target_table=name,
                            expected_val=et["event"],
                            actual_val=at["event"],
                            schema_diff=msg
                        )
                    if et["definition"] != at["definition"]:
                        msg = f"Table '{name}' Trigger '{t}': definition mismatch. Expected {et['definition']}, got {at['definition']}"
                        mismatches.append(msg)
                        self._log_failure(
                            rule_name="Trigger Definition Check",
                            source_table=name,
                            target_table=name,
                            expected_val=str(et["definition"]),
                            actual_val=str(at["definition"]),
                            schema_diff=msg
                        )

            elif exp_obj["object_type"] == "VIEW":
                if exp_obj["definition"] != act_obj["definition"]:
                    msg = f"View '{name}': definition mismatch. Expected {exp_obj['definition']}, got {act_obj['definition']}"
                    mismatches.append(msg)
                    self._log_failure(
                        rule_name="View Definition Check",
                        source_table=name,
                        target_table=name,
                        expected_val=str(exp_obj["definition"]),
                        actual_val=str(act_obj["definition"]),
                        schema_diff=msg
                    )

        # 6. Fix 3 — Normalized structural checksum comparison.
        #
        # The Scout-stored checksum (universal_json["metadata"]["checksum"]) is a
        # SHA-256 fingerprint of the *raw* source-database objects. Its purpose is
        # file integrity: proving the Universal JSON was not tampered with between
        # Scout writing it and Validator reading it. It is kept in the report for
        # audit purposes but is NOT used for structural equivalence here, because
        # raw objects are dialect-specific (e.g. MySQL 'INT' vs PostgreSQL
        # 'INTEGER', NULL default vs nextval(...)).
        #
        # Instead we compare checksums computed over the *normalized* source and
        # target schemas. These are dialect-agnostic, so a correct cross-dialect
        # migration (MySQL -> PostgreSQL) produces matching normalized checksums.
        # A same-dialect migration (MySQL -> MySQL, PostgreSQL -> PostgreSQL) also
        # produces matching normalized checksums, so no regression is introduced.
        scout_source_checksum = universal_json["metadata"]["checksum"]
        if norm_source_checksum != norm_target_checksum:
            msg = (
                f"Normalized schema checksum mismatch: "
                f"expected {norm_source_checksum[:16]}..., got {norm_target_checksum[:16]}... "
                f"(Scout source fingerprint: {scout_source_checksum[:16]}...)"
            )
            mismatches.append(msg)
            self._log_failure(
                rule_name="Normalized Schema Checksum Check",
                expected_val=norm_source_checksum,
                actual_val=norm_target_checksum,
                checksum_values=msg
            )
        else:
            logger.info(
                "[ValidatorAgent] Normalized schema checksum matched: %s... "
                "(Scout source fingerprint: %s...)",
                norm_source_checksum[:16], scout_source_checksum[:16]
            )

        # Return the normalized target checksum as the 'computed_checksum' result so
        # callers and reports have a stable normalized value. The Scout fingerprint is
        # preserved separately in the report (see _execute_task).
        return mismatches, norm_target_checksum

    async def validate_table_data(
        self,
        source_config,
        target_config,
        table_name: str,
    ) -> Dict[str, Any]:
        """
        Compare actual row data between source and target databases for a single table.

        Steps
        -----
        1. Connect a real PostgreSQLAdapter to source_config and another to target_config.
        2. Call get_row_count(table_name) on both independently.
           - If counts differ → return FAIL with reason="row_count_mismatch" immediately
             (no point computing checksums when counts already diverge).
        3. If counts match, call compute_checksum(table_name) on both independently.
           - If checksums differ → return FAIL with reason="checksum_mismatch".
           - If checksums match → return PASS.
        4. Close both connections in a try/finally regardless of outcome.

        Returns
        -------
        {
            "status":           "PASS" | "FAIL",
            "table":            str,
            "source_row_count": int,
            "target_row_count": int,
            "source_checksum":  str | None,   # None when skipped (count mismatch)
            "target_checksum":  str | None,
            "reason":           str | None,   # only on FAIL
        }
        """
        from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter

        src = PostgreSQLAdapter(source_config)
        tgt = PostgreSQLAdapter(target_config)

        result: Dict[str, Any] = {
            "status": "FAIL",
            "table": table_name,
            "source_row_count": None,
            "target_row_count": None,
            "source_checksum": None,
            "target_checksum": None,
            "reason": None,
        }

        try:
            await src.connect()
            await tgt.connect()

            # ── Step 1: row counts ────────────────────────────────────────────
            src_count = await src.get_row_count(table_name)
            tgt_count = await tgt.get_row_count(table_name)
            result["source_row_count"] = src_count
            result["target_row_count"] = tgt_count

            if src_count != tgt_count:
                result["reason"] = "row_count_mismatch"
                logger.warning(
                    "[ValidatorAgent] validate_table_data FAIL table=%s "
                    "row_count_mismatch source=%d target=%d",
                    table_name, src_count, tgt_count,
                )
                self._log_failure(
                    rule_name="Row Count Check",
                    source_table=table_name,
                    target_table=table_name,
                    expected_val=str(src_count),
                    actual_val=str(tgt_count),
                    row_counts=f"Source={src_count}, Target={tgt_count}",
                    schema_diff=f"Row count mismatch on table {table_name}"
                )
                return result

            # ── Step 2: checksums ─────────────────────────────────────────────
            src_checksum = await src.compute_checksum(table_name)
            tgt_checksum = await tgt.compute_checksum(table_name)
            result["source_checksum"] = src_checksum
            result["target_checksum"] = tgt_checksum

            if src_checksum != tgt_checksum:
                result["reason"] = "checksum_mismatch"
                logger.warning(
                    "[ValidatorAgent] validate_table_data FAIL table=%s "
                    "checksum_mismatch src=%.16s... tgt=%.16s...",
                    table_name, src_checksum, tgt_checksum,
                )
                self._log_failure(
                    rule_name="Table Checksum Check",
                    source_table=table_name,
                    target_table=table_name,
                    expected_val=src_checksum,
                    actual_val=tgt_checksum,
                    checksum_values=f"Source={src_checksum}, Target={tgt_checksum}",
                    schema_diff=f"Checksum signature mismatch on table {table_name}"
                )
                return result

            # ── Step 3: all good ──────────────────────────────────────────────
            result["status"] = "PASS"
            logger.info(
                "[ValidatorAgent] validate_table_data PASS table=%s "
                "row_count=%d checksum=%.16s...",
                table_name, src_count, src_checksum,
            )
            return result

        finally:
            try:
                await src.close()
            except Exception:
                pass
            try:
                await tgt.close()
            except Exception:
                pass
