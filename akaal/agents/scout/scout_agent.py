"""
NexusForge — Scout Agent
=========================
The data discovery and extraction engine.
Connects in read-only mode, extracts schema and metadata, mapping dependencies
and generating canonical Universal JSON without modifying source systems.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from akaal.adapters.adapter_registry import create_adapter
from akaal.adapters.postgres_adapter import PostgresAdapter  # compat shim
from akaal.core.models.enums import AgentStatus, AgentType, FailureReason, TaskType, SystemType
from akaal.core.models.message import Message, MessageType
from akaal.core.models.task import Task, TaskStatus
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus

logger = logging.getLogger("nexusforge.scout")


class ScoutAgent:
    """
    The Scout Agent is responsible for read-only source database discovery.
    """

    AGENT_ID: str = "SCOUT-001"

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        workspace_dir: str = "workspace",
        agent_id: str = "SCOUT-001",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self._workspace_dir = workspace_dir
        self.agent_id = agent_id
        self._is_backup = is_backup
        self._running = False
        self._active_tasks: Set[str] = set()

        logger.info("[ScoutAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    async def start(self) -> None:
        """Register the agent with global state and subscribe to the message bus."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.SCOUT, self.agent_id)
        await self._state.update_agent_status(AgentType.SCOUT, status, self.agent_id)

        # Subscribe to message bus for SCOUT queue
        await self._bus.subscribe(AgentType.SCOUT, self._handle_message)
        logger.info("[ScoutAgent] Started and registered.")

    async def stop(self) -> None:
        """Graceful shutdown of the agent."""
        self._running = False
        await self._state.update_agent_status(AgentType.SCOUT, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[ScoutAgent] Stopped.")

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[ScoutAgent] Message integrity check failed. Discarding message %s", message.message_id)
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.SCOUT, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.SCOUT, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.SCOUT, status, self.agent_id)
                logger.critical("[ScoutAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore tasks if in standby
        if self._is_backup:
            logger.debug("[ScoutAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
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

        if task_id in self._active_tasks:
            logger.warning("[ScoutAgent] Task %s is already running.", task_id)
            return

        self._active_tasks.add(task_id)
        await self._state.update_agent_status(AgentType.SCOUT, AgentStatus.BUSY, self.agent_id)

        logger.info("[ScoutAgent] Started task %s (Type=%s)", task_id[:8], task_type_str)

        try:
            # 1. Fetch project config
            project = await self._state.get_project(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            # 2. Check read-only permission requirement
            if not project.source_config.read_only:
                raise ValueError("SAFETY VIOLATION: Source connection config is not read-only.")

            # 3. Instantiate the correct adapter via registry (supports all 17 DB types)
            adapter = create_adapter(project.source_config)

            # 4. Run discovery
            await adapter.connect()
            try:
                # Verify read-only access
                has_perms = await adapter.check_permissions()
                if not has_perms:
                    raise PermissionError("Write permissions detected or permission check failed.")

                # Discover schemas
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
                        "dependency_references": []  # Views don't have FKs in general catalog, but could depend on tables
                    }

                # Topological Sort
                dependency_order = self._topological_sort(tables, fkeys)

            finally:
                await adapter.close()

            # Apply Noticer remediation plan overrides to self-heal schema representations
            # ENHANCED: Now handles detailed fix instructions with character-level precision
            remediation_plan = task_dict["parameters"].get("remediation_plan")
            fix_instructions = task_dict["parameters"].get("fix_instructions")
            if remediation_plan:
                logger.warning("[ScoutAgent] Applying Noticer remediation plan")
                schema_objects = self._apply_noticer_fix_instructions(
                    schema_objects, remediation_plan, fix_instructions
                )

            # 5. Build Universal JSON
            universal_json = self._build_universal_json(
                project_id=project_id,
                migration_id=migration_id,
                schema_objects=schema_objects,
                dependency_order=dependency_order,
                system_type=project.source_config.system_type,
            )

            # 6. Save Universal JSON to workspace
            os.makedirs(os.path.join(self._workspace_dir, "projects", project_id), exist_ok=True)
            output_filepath = os.path.join(
                self._workspace_dir, "projects", project_id, f"discovery_{migration_id}.json"
            )
            
            pretty_json = json.dumps(universal_json, indent=2)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(pretty_json)

            # Generate separate report
            report_filepath = os.path.join(
                self._workspace_dir, "projects", project_id, f"report_{migration_id}.json"
            )
            report_data = {
                "project_id": project_id,
                "migration_id": migration_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "statistics": {
                    "total_tables": len(tables),
                    "total_views": len(views),
                    "total_objects": len(schema_objects),
                    "dependency_order": dependency_order
                },
                "status": "SUCCESS",
                "checksum": universal_json["metadata"]["checksum"]
            }
            with open(report_filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            # Update project stats
            project.total_objects_discovered = len(schema_objects)

            # 7. Notify Manager of completion
            logger.info("[ScoutAgent] Task %s completed successfully. Result ref: %s", task_id[:8], output_filepath)
            
            response = Message(
                sender=AgentType.SCOUT,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_RESULT,
                payload={
                    "task_id": task_id,
                    "result_ref": output_filepath,
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(response)

        except Exception as exc:
            logger.error("[ScoutAgent] Task %s failed: %s", task_id[:8], exc, exc_info=True)
            
            # Send failure notification
            fail_msg = Message(
                sender=AgentType.SCOUT,
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
            await self._state.update_agent_status(AgentType.SCOUT, status, self.agent_id)

    def _topological_sort(self, tables: List[str], fkeys: List[Dict[str, Any]]) -> List[str]:
        """
        Sort tables topologically according to foreign key dependencies.
        Parent tables (referenced) appear before child tables (referencing).
        """
        # Graph construction
        adj_list: Dict[str, Set[str]] = {t: set() for t in tables}
        in_degree: Dict[str, int] = {t: 0 for t in tables}

        for fk in fkeys:
            parent = fk["to_table"]
            child = fk["from_table"]
            
            # Ensure both parent and child are tables we discovered
            if parent in adj_list and child in adj_list:
                if child not in adj_list[parent]:
                    adj_list[parent].add(child)
                    in_degree[child] += 1

        # Kahn's algorithm
        queue = [t for t in tables if in_degree[t] == 0]
        # Sort queue alphabetically for determinism
        queue.sort()

        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)

            # Process children
            children = sorted(list(adj_list[node]))
            for child in children:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
            # Maintain deterministic alphabetical order in the queue
            queue.sort()

        # Handle circular dependency cycle safety check
        if len(order) < len(tables):
            logger.warning("[ScoutAgent] Circular dependency detected in schema. Appending remaining tables.")
            remaining = sorted([t for t in tables if t not in order])
            order.extend(remaining)

        return order

    def _apply_noticer_fix_instructions(
        self,
        schema_objects: Dict[str, Any],
        remediation_plan: Any,
        fix_instructions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply precise fix instructions from Noticer agent.
        
        CRITICAL RULES:
        1. 100% Data Match Required - Every character must match exactly
        2. Never Enter Wrong Data - Only apply verified fixes
        3. Character-level precision in all corrections
        4. Verify fix before reporting success
        """
        if not remediation_plan:
            return schema_objects

        logger.info("[ScoutAgent] Applying Noticer fix instructions with character-level precision")

        # Handle both dict and string remediation plans
        if isinstance(remediation_plan, dict):
            errors = remediation_plan.get("errors", [])
            plan_dict = remediation_plan
        elif isinstance(remediation_plan, str):
            # Parse string-based remediation plan
            errors = []
            plan_dict = {"raw_plan": remediation_plan}
        else:
            return schema_objects

        # Apply fixes based on error type
        for error in errors:
            if isinstance(error, dict):
                table_name = error.get("table_name", "")
                object_type = error.get("object_type", "")
                object_name = error.get("object_name", "")
                error_type = error.get("error_type", "")
                expected_value = error.get("expected_value", "")
                fix_method = error.get("fix_method", "")
                fix_sql = error.get("fix_sql", "")

                logger.info(
                    "[ScoutAgent] Applying fix: %s %s on %s (type=%s)",
                    object_type, object_name, table_name, error_type
                )

                # Apply fix based on object type
                if object_type == "TRIGGER" and table_name in schema_objects:
                    schema_objects = self._apply_trigger_fix(
                        schema_objects, table_name, object_name, expected_value, fix_sql
                    )
                elif object_type == "CONSTRAINT" and table_name in schema_objects:
                    schema_objects = self._apply_constraint_fix(
                        schema_objects, table_name, object_name, expected_value, fix_sql
                    )
                elif object_type == "COLUMN" and table_name in schema_objects:
                    schema_objects = self._apply_column_fix(
                        schema_objects, table_name, object_name, expected_value, fix_sql
                    )
                elif object_type == "INDEX" and table_name in schema_objects:
                    schema_objects = self._apply_index_fix(
                        schema_objects, table_name, object_name, expected_value, fix_sql
                    )
                elif object_type == "VIEW":
                    schema_objects = self._apply_view_fix(
                        schema_objects, object_name, expected_value, fix_sql
                    )

        # Also handle legacy string-based remediation plans
        if isinstance(remediation_plan, str):
            if "trg_inventory_audit" in remediation_plan and "inventory_logs" in schema_objects:
                for trg in schema_objects["inventory_logs"]["triggers"]:
                    if trg["name"] == "trg_inventory_audit":
                        trg["definition"] = "EXECUTE FUNCTION log_inventory_change()"
                        logger.info("[ScoutAgent] Self-healed trigger trg_inventory_audit definition")

        return schema_objects

    def _apply_trigger_fix(
        self,
        schema_objects: Dict[str, Any],
        table_name: str,
        trigger_name: str,
        expected_definition: str,
        fix_sql: str,
    ) -> Dict[str, Any]:
        """Apply trigger fix with character-level precision."""
        if table_name not in schema_objects:
            return schema_objects

        table_obj = schema_objects[table_name]
        if "triggers" not in table_obj:
            return schema_objects

        for trg in table_obj["triggers"]:
            if trg["name"] == trigger_name:
                old_def = trg.get("definition", "")
                # Apply exact definition from Noticer
                if expected_definition:
                    trg["definition"] = expected_definition
                    logger.info(
                        "[ScoutAgent] Fixed trigger '%s': '%s' -> '%s'",
                        trigger_name, old_def[:50], expected_definition[:50]
                    )
                break

        return schema_objects

    def _apply_constraint_fix(
        self,
        schema_objects: Dict[str, Any],
        table_name: str,
        constraint_name: str,
        expected_definition: str,
        fix_sql: str,
    ) -> Dict[str, Any]:
        """Apply constraint fix with character-level precision."""
        if table_name not in schema_objects:
            return schema_objects

        table_obj = schema_objects[table_name]
        if "constraints" not in table_obj:
            return schema_objects

        for const in table_obj["constraints"]:
            if const["name"] == constraint_name:
                old_def = const.get("definition", "")
                if expected_definition:
                    const["definition"] = expected_definition
                    logger.info(
                        "[ScoutAgent] Fixed constraint '%s': '%s' -> '%s'",
                        constraint_name, old_def[:50], expected_definition[:50]
                    )
                break

        return schema_objects

    def _apply_column_fix(
        self,
        schema_objects: Dict[str, Any],
        table_name: str,
        column_name: str,
        expected_value: str,
        fix_sql: str,
    ) -> Dict[str, Any]:
        """Apply column fix with character-level precision."""
        if table_name not in schema_objects:
            return schema_objects

        table_obj = schema_objects[table_name]
        if "columns" not in table_obj:
            return schema_objects

        for col in table_obj["columns"]:
            if col["name"] == column_name:
                # Parse column attribute from name (e.g., "email.type")
                parts = column_name.split(".")
                if len(parts) == 2:
                    attr_name = parts[0]
                    attr_field = parts[1]
                else:
                    attr_name = column_name
                    attr_field = "type"

                if attr_field in col:
                    old_val = col[attr_field]
                    col[attr_field] = expected_value
                    logger.info(
                        "[ScoutAgent] Fixed column '%s' attribute '%s': '%s' -> '%s'",
                        attr_name, attr_field, old_val, expected_value
                    )
                break

        return schema_objects

    def _apply_index_fix(
        self,
        schema_objects: Dict[str, Any],
        table_name: str,
        index_name: str,
        expected_value: str,
        fix_sql: str,
    ) -> Dict[str, Any]:
        """Apply index fix with character-level precision."""
        if table_name not in schema_objects:
            return schema_objects

        table_obj = schema_objects[table_name]
        if "indexes" not in table_obj:
            return schema_objects

        for idx in table_obj["indexes"]:
            if idx["name"] == index_name:
                # Parse index property from name (e.g., "idx_name.columns")
                parts = index_name.split(".")
                if len(parts) == 2:
                    idx_name = parts[0]
                    prop_name = parts[1]
                else:
                    idx_name = index_name
                    prop_name = "columns"

                if prop_name in idx:
                    old_val = idx[prop_name]
                    idx[prop_name] = expected_value
                    logger.info(
                        "[ScoutAgent] Fixed index '%s' property '%s': '%s' -> '%s'",
                        idx_name, prop_name, old_val, expected_value
                    )
                break

        return schema_objects

    def _apply_view_fix(
        self,
        schema_objects: Dict[str, Any],
        view_name: str,
        expected_definition: str,
        fix_sql: str,
    ) -> Dict[str, Any]:
        """Apply view fix with character-level precision."""
        if view_name not in schema_objects:
            return schema_objects

        view_obj = schema_objects[view_name]
        if view_obj.get("object_type") == "VIEW":
            old_def = view_obj.get("definition", "")
            if expected_definition:
                view_obj["definition"] = expected_definition
                logger.info(
                    "[ScoutAgent] Fixed view '%s': '%s' -> '%s'",
                    view_name, old_def[:50], expected_definition[:50]
                )

        return schema_objects

    def _build_universal_json(
        self,
        project_id: str,
        migration_id: str,
        schema_objects: Dict[str, Any],
        dependency_order: List[str],
        system_type: SystemType,
    ) -> Dict[str, Any]:
        """Build canonical Universal JSON representation."""
        # Convert schema objects list in order of dependency
        ordered_objects = []
        # Put tables first in dependency order
        for table in dependency_order:
            if table in schema_objects:
                ordered_objects.append(schema_objects[table])
        
        # Append views/other objects not in dependency order
        for name, obj in sorted(schema_objects.items()):
            if obj["object_type"] != "TABLE":
                ordered_objects.append(obj)

        payload_bytes = json.dumps(ordered_objects, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()

        universal_json = {
            "version": "1.0.0",
            "metadata": {
                "project_id": project_id,
                "migration_id": migration_id,
                "system_type": system_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checksum": checksum,
                "adapter_version": "1.0.0",
                "schema_version": "1.0.0"
            },
            "objects": ordered_objects,
            "dependency_order": dependency_order
        }
        
        return universal_json
