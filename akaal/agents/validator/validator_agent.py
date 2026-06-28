"""
NexusForge — Validator Agent
============================
The integrity enforcement engine.
Verifies data and schema structures, compares against the canonical Universal JSON,
and validates that the target migrations match the source system's schema.
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

    def _perform_validation(
        self,
        scanned_objects: Dict[str, Any],
        universal_json: Dict[str, Any]
    ) -> Tuple[List[str], str]:
        """
        Compares scanned database objects against Universal JSON specification.
        Returns a list of mismatches (empty if identical) and the computed checksum of the scanned objects.
        """
        mismatches: List[str] = []
        universal_objects: List[Dict[str, Any]] = universal_json.get("objects", [])
        universal_by_name = {obj["object_name"]: obj for obj in universal_objects}

        # 1. Compare total presence and names of objects
        scanned_names = set(scanned_objects.keys())
        expected_names = set(universal_by_name.keys())

        missing_objects = expected_names - scanned_names
        extra_objects = scanned_names - expected_names

        for name in missing_objects:
            mismatches.append(f"Missing object: '{name}'")
        for name in extra_objects:
            mismatches.append(f"Extra object: '{name}'")

        # 2. Detailed attribute validation for common objects
        for name in expected_names & scanned_names:
            expected_obj = universal_by_name[name]
            actual_obj = scanned_objects[name]

            # Compare type
            if expected_obj["object_type"] != actual_obj["object_type"]:
                mismatches.append(
                    f"Object '{name}' type mismatch: expected {expected_obj['object_type']}, got {actual_obj['object_type']}"
                )
                continue

            if expected_obj["object_type"] == "TABLE":
                # Compare columns
                expected_cols = {col["name"]: col for col in expected_obj.get("columns", [])}
                actual_cols = {col["name"]: col for col in actual_obj.get("columns", [])}

                missing_cols = set(expected_cols.keys()) - set(actual_cols.keys())
                extra_cols = set(actual_cols.keys()) - set(expected_cols.keys())

                for c in missing_cols:
                    mismatches.append(f"Table '{name}': missing column '{c}'")
                for c in extra_cols:
                    mismatches.append(f"Table '{name}': extra column '{c}'")

                for c in set(expected_cols.keys()) & set(actual_cols.keys()):
                    ec = expected_cols[c]
                    ac = actual_cols[c]

                    if ec["type"] != ac["type"]:
                        mismatches.append(
                            f"Table '{name}' Column '{c}': type mismatch. Expected {ec['type']}, got {ac['type']}"
                        )
                    if ec["nullable"] != ac["nullable"]:
                        mismatches.append(
                            f"Table '{name}' Column '{c}': nullable mismatch. Expected {ec['nullable']}, got {ac['nullable']}"
                        )
                    if ec.get("default") != ac.get("default"):
                        mismatches.append(
                            f"Table '{name}' Column '{c}': default value mismatch. Expected {ec.get('default')}, got {ac.get('default')}"
                        )

                # Compare indexes
                expected_indexes = {idx["name"]: idx for idx in expected_obj.get("indexes", [])}
                actual_indexes = {idx["name"]: idx for idx in actual_obj.get("indexes", [])}

                missing_idx = set(expected_indexes.keys()) - set(actual_indexes.keys())
                extra_idx = set(actual_indexes.keys()) - set(expected_indexes.keys())

                for i in missing_idx:
                    mismatches.append(f"Table '{name}': missing index '{i}'")
                for i in extra_idx:
                    mismatches.append(f"Table '{name}': extra index '{i}'")

                for i in set(expected_indexes.keys()) & set(actual_indexes.keys()):
                    ei = expected_indexes[i]
                    ai = actual_indexes[i]
                    if ei["columns"] != ai["columns"]:
                        mismatches.append(
                            f"Table '{name}' Index '{i}': columns mismatch. Expected {ei['columns']}, got {ai['columns']}"
                        )
                    if ei["unique"] != ai["unique"]:
                        mismatches.append(
                            f"Table '{name}' Index '{i}': uniqueness mismatch. Expected {ei['unique']}, got {ai['unique']}"
                        )

                # Compare constraints
                expected_consts = {c["name"]: c for c in expected_obj.get("constraints", [])}
                actual_consts = {c["name"]: c for c in actual_obj.get("constraints", [])}

                missing_const = set(expected_consts.keys()) - set(actual_consts.keys())
                extra_const = set(actual_consts.keys()) - set(expected_consts.keys())

                for c in missing_const:
                    mismatches.append(f"Table '{name}': missing constraint '{c}'")
                for c in extra_const:
                    mismatches.append(f"Table '{name}': extra constraint '{c}'")

                for c in set(expected_consts.keys()) & set(actual_consts.keys()):
                    ec = expected_consts[c]
                    ac = actual_consts[c]
                    if ec["type"] != ac["type"]:
                        mismatches.append(
                            f"Table '{name}' Constraint '{c}': type mismatch. Expected {ec['type']}, got {ac['type']}"
                        )
                    if ec.get("definition") != ac.get("definition"):
                        mismatches.append(
                            f"Table '{name}' Constraint '{c}': definition mismatch. Expected {ec.get('definition')}, got {ac.get('definition')}"
                        )

                # Compare dependency references / foreign keys
                expected_refs = {r["constraint_name"]: r for r in expected_obj.get("dependency_references", [])}
                actual_refs = {r["constraint_name"]: r for r in actual_obj.get("dependency_references", [])}

                missing_ref = set(expected_refs.keys()) - set(actual_refs.keys())
                extra_ref = set(actual_refs.keys()) - set(expected_refs.keys())

                for r in missing_ref:
                    mismatches.append(f"Table '{name}': missing foreign key constraint '{r}'")
                for r in extra_ref:
                    mismatches.append(f"Table '{name}': extra foreign key constraint '{r}'")

                for r in set(expected_refs.keys()) & set(actual_refs.keys()):
                    er = expected_refs[r]
                    ar = actual_refs[r]
                    if er["from_column"] != ar["from_column"]:
                        mismatches.append(
                            f"Table '{name}' Foreign Key '{r}': source column mismatch. Expected {er['from_column']}, got {ar['from_column']}"
                        )
                    if er["target_table"] != ar["target_table"]:
                        mismatches.append(
                            f"Table '{name}' Foreign Key '{r}': target table mismatch. Expected {er['target_table']}, got {ar['target_table']}"
                        )
                    if er["target_column"] != ar["target_column"]:
                        mismatches.append(
                            f"Table '{name}' Foreign Key '{r}': target column mismatch. Expected {er['target_column']}, got {ar['target_column']}"
                        )

                # Compare triggers
                expected_triggers = {t["name"]: t for t in expected_obj.get("triggers", [])}
                actual_triggers = {t["name"]: t for t in actual_obj.get("triggers", [])}

                missing_triggers = set(expected_triggers.keys()) - set(actual_triggers.keys())
                extra_triggers = set(actual_triggers.keys()) - set(expected_triggers.keys())

                for t in missing_triggers:
                    mismatches.append(f"Table '{name}': missing trigger '{t}'")
                for t in extra_triggers:
                    mismatches.append(f"Table '{name}': extra trigger '{t}'")

                for t in set(expected_triggers.keys()) & set(actual_triggers.keys()):
                    et = expected_triggers[t]
                    at = actual_triggers[t]
                    if et["event"] != at["event"]:
                        mismatches.append(
                            f"Table '{name}' Trigger '{t}': event mismatch. Expected {et['event']}, got {at['event']}"
                        )
                    if et.get("definition") != at.get("definition"):
                        mismatches.append(
                            f"Table '{name}' Trigger '{t}': definition mismatch. Expected {et.get('definition')}, got {at.get('definition')}"
                        )

            elif expected_obj["object_type"] == "VIEW":
                if expected_obj.get("definition") != actual_obj.get("definition"):
                    mismatches.append(
                        f"View '{name}': definition mismatch. Expected {expected_obj.get('definition')}, got {actual_obj.get('definition')}"
                    )

        # 3. Compute checksum on scanned objects
        # We must reconstruct the ordered list using the same ordering logic as Scout
        ordered_scanned = []
        dependency_order = universal_json.get("dependency_order", [])

        # Put tables first in dependency order
        for table in dependency_order:
            if table in scanned_objects:
                ordered_scanned.append(scanned_objects[table])
        
        # Append views/other objects not in dependency order
        for n, obj in sorted(scanned_objects.items()):
            if obj["object_type"] != "TABLE":
                ordered_scanned.append(obj)

        payload_bytes = json.dumps(ordered_scanned, sort_keys=True).encode("utf-8")
        computed_checksum = hashlib.sha256(payload_bytes).hexdigest()

        # 4. Compare checksums
        expected_checksum = universal_json["metadata"]["checksum"]
        if expected_checksum != computed_checksum:
            mismatches.append(
                f"Checksum signature mismatch: expected {expected_checksum[:16]}..., got {computed_checksum[:16]}..."
            )

        return mismatches, computed_checksum
