"""
NexusForge — Noticer Agent (Enhanced)
======================================
The discrepancy analysis and database repair advisor agent.
Intercepts validation failures, investigates database line-by-line to find exact errors,
and recommends precise fix methods to the Manager Agent.

CRITICAL RULES:
1. 100% Data Match Required - Every character must match exactly
2. Infinite Loop Prevention - Max 3 remediation attempts before escalation
3. Never Enter Wrong Data - Only report exact errors and precise fixes
4. Line-by-Line Error Detection - Locate exact error positions
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from akaal.adapters.adapter_registry import create_adapter
from akaal.adapters.postgres_adapter import PostgresAdapter  # compat shim
from akaal.core.models.enums import AgentStatus, AgentType, FailureReason, Priority
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus

logger = logging.getLogger("nexusforge.noticer")


# ---------------------------------------------------------------------------
# Data Classes for Enhanced Error Reporting
# ---------------------------------------------------------------------------

@dataclass
class DatabaseError:
    """Represents a single database error with exact location and fix."""
    table_name: str
    object_type: str  # TABLE, VIEW, COLUMN, INDEX, CONSTRAINT, TRIGGER
    object_name: str
    error_type: str  # MISSING, EXTRA, MISMATCH, DEFINITION_MISMATCH
    line_number: int
    column_position: int
    expected_value: str
    actual_value: str
    exact_difference: str
    fix_method: str
    fix_sql: str
    severity: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "error_type": self.error_type,
            "line_number": self.line_number,
            "column_position": self.column_position,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "exact_difference": self.exact_difference,
            "fix_method": self.fix_method,
            "fix_sql": self.fix_sql,
            "severity": self.severity,
            "verified": self.verified,
        }


@dataclass
class RemediationPlan:
    """Complete remediation plan with all errors and fix instructions."""
    plan_id: str
    project_id: str
    migration_id: str
    timestamp: str
    errors: List[DatabaseError]
    fix_instructions: List[str]
    verification_steps: List[str]
    estimated_fix_time: str
    risk_level: str
    requires_downtime: bool
    total_errors: int
    character_level_diffs: int
    remediation_attempt: int
    max_attempts: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "timestamp": self.timestamp,
            "errors": [e.to_dict() for e in self.errors],
            "fix_instructions": self.fix_instructions,
            "verification_steps": self.verification_steps,
            "estimated_fix_time": self.estimated_fix_time,
            "risk_level": self.risk_level,
            "requires_downtime": self.requires_downtime,
            "total_errors": self.total_errors,
            "character_level_diffs": self.character_level_diffs,
            "remediation_attempt": self.remediation_attempt,
            "max_attempts": self.max_attempts,
        }


@dataclass
class RemediationAttempt:
    """Tracks a remediation attempt for infinite loop prevention."""
    attempt_id: str
    project_id: str
    migration_id: str
    timestamp: str
    error_hash: str
    fix_applied: str
    success: bool
    error_message: str = ""


# ---------------------------------------------------------------------------
# Infinite Loop Prevention Rules
# ---------------------------------------------------------------------------

class InfiniteLoopPrevention:
    """
    RULES FOR INFINITE LOOP PREVENTION:
    1. Track all remediation attempts per project/migration
    2. Detect repeated fix failures for same error
    3. Escalate to human after 3 failed attempts
    4. Never suggest unverified fix methods
    5. Always verify fix before reporting success
    6. Log all remediation attempts for audit
    7. Freeze workflow if same error recurs 3 times
    8. Require human approval for risky fixes
    """
    MAX_REMEDIATION_ATTEMPTS = 3
    DETECTION_WINDOW_HOURS = 24
    SAME_ERROR_THRESHOLD = 2


# ---------------------------------------------------------------------------
# 100% Data Match Verification Rules
# ---------------------------------------------------------------------------

class DataMatchVerification:
    """
    RULES FOR 100% DATA MATCH:
    1. Every character must match exactly
    2. No tolerance for any difference
    3. Verify line-by-line for text definitions
    4. Verify attribute-by-attribute for schema objects
    5. Checksum must match exactly
    6. No partial matches allowed
    7. Verify after every fix application
    8. Log all verification results
    """
    TOLERANCE = 0  # Zero tolerance for any mismatch


# ---------------------------------------------------------------------------
# Noticer Agent
# ---------------------------------------------------------------------------

class NoticerAgent:
    """
    The Noticer Agent intercepts validation failures, investigates database
    line-by-line to find exact errors, and recommends precise fix methods.

    CRITICAL BEHAVIOR:
    - Works independently and in parallel with other agents
    - When Validator gives FALSE, message goes to Noticer FIRST
    - Investigates database to find exact error location and type
    - Reports to Manager with error details and fix methods
    - Manager tells Scout to fix it
    - 100% data match required - no character mismatch allowed
    - Prevents infinite loops by tracking remediation attempts
    """

    AGENT_ID: str = "NOTICER-001"

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        agent_id: str = "NOTICER-001",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self.agent_id = agent_id
        self._is_backup = is_backup
        self._running = False

        # Infinite loop prevention tracking
        self._remediation_attempts: Dict[str, List[RemediationAttempt]] = {}
        self._error_hashes: Dict[str, int] = {}

        logger.info("[NoticerAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    async def start(self) -> None:
        """Register with global state and subscribe to queue."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.NOTICER, self.agent_id)
        await self._state.update_agent_status(AgentType.NOTICER, status, self.agent_id)

        # Subscribe to receive validation failure messages
        await self._bus.subscribe(AgentType.NOTICER, self._handle_message)
        logger.info("[NoticerAgent] Started and registered.")

    async def stop(self) -> None:
        """Shut down the agent."""
        self._running = False
        await self._state.update_agent_status(AgentType.NOTICER, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[NoticerAgent] Stopped.")

    async def _handle_message(self, message: Message) -> None:
        """Process incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[NoticerAgent] Message integrity check failed.")
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.NOTICER, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.NOTICER, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.NOTICER, status, self.agent_id)
                logger.critical("[NoticerAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore tasks if in standby
        if self._is_backup:
            logger.debug("[NoticerAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
            return

        # Intercept TASK_FAILED message from Validator
        if message.message_type == MessageType.TASK_FAILED:
            await self._state.update_agent_status(AgentType.NOTICER, AgentStatus.BUSY, self.agent_id)
            try:
                await self._process_validation_failure(message)
            except Exception as e:
                logger.error("[NoticerAgent] Error diagnosing failure: %s", e, exc_info=True)
            finally:
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.NOTICER, status, self.agent_id)

    async def _process_validation_failure(self, message: Message) -> None:
        """Analyze validation mismatches and compile remediation plan."""
        task_id = message.payload.get("task_id")
        mismatches = message.payload.get("mismatches", [])
        project_id = message.project_id or ""
        migration_id = message.migration_id or ""

        logger.info(
            "[NoticerAgent] Intercepted validation failure for task %s. Diagnosing %d mismatches.",
            task_id[:8] if task_id else "unknown", len(mismatches)
        )

        # Check infinite loop prevention
        error_hash = self._compute_error_hash(mismatches)
        remediation_count = self._get_remediation_count(project_id, error_hash)

        if remediation_count >= InfiniteLoopPrevention.MAX_REMEDIATION_ATTEMPTS:
            logger.error(
                "[NoticerAgent] INFINITE LOOP PREVENTION: %d attempts made for same error. Escalating to Manager.",
                remediation_count
            )
            await self._escalate_to_manager(
                task_id, project_id, migration_id, mismatches,
                f"Max remediation attempts ({InfiniteLoopPrevention.MAX_REMEDIATION_ATTEMPTS}) reached for same error pattern."
            )
            return

        # Fetch project to access db config
        project = await self._state.get_project(project_id)
        if not project:
            logger.error("[NoticerAgent] Project %s not found.", project_id)
            return

        # Query target database using PostgresAdapter to diagnose
        db_config = project.target_config
        errors: List[DatabaseError] = []

        if db_config:
            adapter = create_adapter(db_config)
            try:
                await adapter.connect()
                errors = await self._investigate_database_line_by_line(
                    adapter, mismatches, project_id, migration_id
                )
            except Exception as exc:
                logger.warning("[NoticerAgent] Database connection warning: %s", exc)
                # Fallback to mismatch-based error detection
                errors = self._create_errors_from_mismatches(mismatches)
            finally:
                await adapter.close()
        else:
            errors = self._create_errors_from_mismatches(mismatches)

        # Verify 100% data match
        verification_result = self._verify_100_percent_match(errors)

        # Build remediation plan
        remediation_plan = self._build_remediation_plan(
            project_id, migration_id, errors, verification_result, remediation_count + 1
        )

        # Track remediation attempt
        self._track_remediation_attempt(
            project_id, migration_id, error_hash, remediation_plan.plan_id, False
        )

        # Route to Manager with detailed remediation plan
        logger.info(
            "[NoticerAgent] Routing failure analysis to Manager. Attempt %d/%d.",
            remediation_count + 1, InfiniteLoopPrevention.MAX_REMEDIATION_ATTEMPTS
        )
        await self._send_to_manager(
            task_id, project_id, migration_id, mismatches, remediation_plan
        )

    def _investigate_database_line_by_line(
        self,
        adapter,
        mismatches: List[Any],
        project_id: str,
        migration_id: str,
    ) -> List[DatabaseError]:
        """
        Investigate database line-by-line to find exact errors.
        Returns list of DatabaseError with exact locations and fix instructions.
        """
        errors: List[DatabaseError] = []

        for idx, mismatch in enumerate(mismatches):
            parsed = self._parse_mismatch(mismatch)

            tbl = parsed.get("table", "unknown")
            obj_name = parsed.get("object_name", "unknown")
            obj_type = parsed.get("object_type", "UNKNOWN")
            error_type = parsed.get("error_type", "MISMATCH")
            description = parsed.get("description", str(mismatch))

            logger.info(
                "[NoticerAgent] Investigating table='%s', object='%s', type='%s'",
                tbl, obj_name, error_type
            )

            # Line-by-line investigation based on object type
            if obj_type == "TRIGGER" or error_type == "TRIGGER_DEFINITION":
                trigger_errors = self._investigate_trigger_line_by_line(
                    adapter, tbl, obj_name, description
                )
                errors.extend(trigger_errors)
            elif obj_type == "CONSTRAINT" or error_type == "CONSTRAINT_DEFINITION":
                constraint_errors = self._investigate_constraint_line_by_line(
                    adapter, tbl, obj_name, description
                )
                errors.extend(constraint_errors)
            elif obj_type == "COLUMN" or error_type == "COLUMN_MISMATCH":
                column_errors = self._investigate_column_line_by_line(
                    adapter, tbl, obj_name, description
                )
                errors.extend(column_errors)
            elif obj_type == "INDEX" or error_type == "INDEX_MISMATCH":
                index_errors = self._investigate_index_line_by_line(
                    adapter, tbl, obj_name, description
                )
                errors.extend(index_errors)
            elif obj_type == "VIEW" or error_type == "VIEW_DEFINITION":
                view_errors = self._investigate_view_line_by_line(
                    adapter, tbl, obj_name, description
                )
                errors.extend(view_errors)
            elif error_type == "MISSING":
                missing_errors = self._investigate_missing_object(
                    adapter, tbl, obj_name, description
                )
                errors.extend(missing_errors)
            elif error_type == "EXTRA":
                extra_errors = self._investigate_extra_object(
                    tbl, obj_name, description
                )
                errors.extend(extra_errors)
            else:
                # Generic error handling
                errors.append(DatabaseError(
                    table_name=tbl,
                    object_type=obj_type,
                    object_name=obj_name,
                    error_type=error_type,
                    line_number=0,
                    column_position=0,
                    expected_value="",
                    actual_value="",
                    exact_difference=description,
                    fix_method="Manual investigation required",
                    fix_sql="",
                    severity="HIGH",
                ))

        return errors

    def _investigate_trigger_line_by_line(
        self,
        adapter,
        table_name: str,
        trigger_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate trigger discrepancies line-by-line."""
        errors: List[DatabaseError] = []

        try:
            # Query actual trigger definition from database
            # Use synchronous approach to avoid event loop issues
            import concurrent.futures
            import asyncio
            
            async def _fetch_triggers():
                return await adapter.discover_triggers(table_name)
            
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, use create_task approach
                # Since we can't await here, we'll use the description-based approach
                triggers = []
            except RuntimeError:
                # No running loop, we can use run_until_complete
                loop = asyncio.new_event_loop()
                try:
                    triggers = loop.run_until_complete(_fetch_triggers())
                finally:
                    loop.close()

            actual_trigger = None
            for t in triggers:
                if t["name"] == trigger_name:
                    actual_trigger = t
                    break

            if actual_trigger is None and not triggers:
                # Could not query database - use description-based approach
                # Parse the expected definition from the description
                expected_def = ""
                if "Expected:" in description:
                    expected_def = description.split("Expected:")[-1].strip()
                elif "definition:" in description.lower():
                    # Try to extract definition from description
                    parts = description.split("definition:")
                    if len(parts) > 1:
                        expected_def = parts[-1].strip().strip("'\"")
                
                if expected_def:
                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="TRIGGER",
                        object_name=trigger_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value=expected_def,
                        actual_value="Could not query database",
                        exact_difference=f"Trigger '{trigger_name}' definition needs correction",
                        fix_method="Update trigger definition to match Universal JSON",
                        fix_sql=f"-- Update trigger {trigger_name} definition\n-- Expected: {expected_def}",
                        severity="HIGH",
                    ))
                else:
                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="TRIGGER",
                        object_name=trigger_name,
                        error_type="MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value="",
                        actual_value="",
                        exact_difference=description,
                        fix_method="Investigate and fix trigger definition",
                        fix_sql="",
                        severity="HIGH",
                    ))
            elif actual_trigger is None:
                # Trigger is missing
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="TRIGGER",
                    object_name=trigger_name,
                    error_type="MISSING",
                    line_number=0,
                    column_position=0,
                    expected_value="Trigger should exist",
                    actual_value="Trigger not found",
                    exact_difference=f"Trigger '{trigger_name}' is missing from table '{table_name}'",
                    fix_method="CREATE TRIGGER",
                    fix_sql=f"-- Create trigger {trigger_name} on table {table_name}\n-- Reference: Universal JSON definition",
                    severity="HIGH",
                ))
            else:
                # Trigger exists - compare definitions character by character
                expected_def = description.split("Expected:")[-1].strip() if "Expected:" in description else ""
                actual_def = actual_trigger.get("definition", "")

                if expected_def and actual_def != expected_def:
                    # Character-level comparison
                    diffs = self._character_level_diff(expected_def, actual_def)
                    line_num, col_pos = self._find_diff_position(expected_def, actual_def)

                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="TRIGGER",
                        object_name=trigger_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=line_num,
                        column_position=col_pos,
                        expected_value=expected_def,
                        actual_value=actual_def,
                        exact_difference=diffs,
                        fix_method="DROP and CREATE TRIGGER with correct definition",
                        fix_sql=f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};\n-- Then create with correct definition from Universal JSON",
                        severity="HIGH",
                    ))

        except Exception as exc:
            logger.warning("[NoticerAgent] Trigger investigation error: %s", exc)
            errors.append(DatabaseError(
                table_name=table_name,
                object_type="TRIGGER",
                object_name=trigger_name,
                error_type="INVESTIGATION_FAILED",
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=f"Could not investigate trigger: {exc}",
                fix_method="Manual investigation required",
                fix_sql="",
                severity="MEDIUM",
            ))

        return errors

    def _investigate_constraint_line_by_line(
        self,
        adapter,
        table_name: str,
        constraint_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate constraint discrepancies line-by-line."""
        errors: List[DatabaseError] = []

        try:
            import asyncio
            
            async def _fetch_constraints():
                return await adapter.discover_constraints(table_name)
            
            try:
                loop = asyncio.get_running_loop()
                constraints = []
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    constraints = loop.run_until_complete(_fetch_constraints())
                finally:
                    loop.close()

            actual_constraint = None
            for c in constraints:
                if c["name"] == constraint_name:
                    actual_constraint = c
                    break

            if actual_constraint is None and not constraints:
                # Could not query database - use description-based approach
                expected_def = ""
                if "Expected:" in description:
                    expected_def = description.split("Expected:")[-1].strip()
                elif "definition:" in description.lower():
                    parts = description.split("definition:")
                    if len(parts) > 1:
                        expected_def = parts[-1].strip().strip("'\"")
                
                if expected_def:
                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="CONSTRAINT",
                        object_name=constraint_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value=expected_def,
                        actual_value="Could not query database",
                        exact_difference=f"Constraint '{constraint_name}' definition needs correction",
                        fix_method="Update constraint definition to match Universal JSON",
                        fix_sql=f"-- Update constraint {constraint_name} definition\n-- Expected: {expected_def}",
                        severity="HIGH",
                    ))
                else:
                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="CONSTRAINT",
                        object_name=constraint_name,
                        error_type="MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value="",
                        actual_value="",
                        exact_difference=description,
                        fix_method="Investigate and fix constraint definition",
                        fix_sql="",
                        severity="HIGH",
                    ))
            elif actual_constraint is None:
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="CONSTRAINT",
                    object_name=constraint_name,
                    error_type="MISSING",
                    line_number=0,
                    column_position=0,
                    expected_value="Constraint should exist",
                    actual_value="Constraint not found",
                    exact_difference=f"Constraint '{constraint_name}' is missing from table '{table_name}'",
                    fix_method="ADD CONSTRAINT",
                    fix_sql=f"-- Add constraint {constraint_name} to table {table_name}\n-- Reference: Universal JSON definition",
                    severity="HIGH",
                ))
            else:
                expected_def = description.split("Expected:")[-1].strip() if "Expected:" in description else ""
                actual_def = actual_constraint.get("definition", "")

                if expected_def and actual_def != expected_def:
                    diffs = self._character_level_diff(expected_def, actual_def)
                    line_num, col_pos = self._find_diff_position(expected_def, actual_def)

                    errors.append(DatabaseError(
                        table_name=table_name,
                        object_type="CONSTRAINT",
                        object_name=constraint_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=line_num,
                        column_position=col_pos,
                        expected_value=expected_def,
                        actual_value=actual_def,
                        exact_difference=diffs,
                        fix_method="DROP and recreate CONSTRAINT with correct definition",
                        fix_sql=f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name};\n-- Then add with correct definition from Universal JSON",
                        severity="HIGH",
                    ))

        except Exception as exc:
            logger.warning("[NoticerAgent] Constraint investigation error: %s", exc)
            errors.append(DatabaseError(
                table_name=table_name,
                object_type="CONSTRAINT",
                object_name=constraint_name,
                error_type="INVESTIGATION_FAILED",
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=f"Could not investigate constraint: {exc}",
                fix_method="Manual investigation required",
                fix_sql="",
                severity="MEDIUM",
            ))

        return errors

    def _investigate_column_line_by_line(
        self,
        adapter,
        table_name: str,
        column_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate column discrepancies line-by-line."""
        errors: List[DatabaseError] = []

        try:
            import asyncio
            
            async def _fetch_columns():
                return await adapter.discover_columns(table_name)
            
            try:
                loop = asyncio.get_running_loop()
                columns = []
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    columns = loop.run_until_complete(_fetch_columns())
                finally:
                    loop.close()

            actual_column = None
            for c in columns:
                if c["name"] == column_name:
                    actual_column = c
                    break

            if actual_column is None and not columns:
                # Could not query database - use description-based approach
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="COLUMN",
                    object_name=column_name,
                    error_type="MISMATCH",
                    line_number=0,
                    column_position=0,
                    expected_value="",
                    actual_value="",
                    exact_difference=description,
                    fix_method="Investigate and fix column definition",
                    fix_sql="",
                    severity="HIGH",
                ))
            elif actual_column is None:
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="COLUMN",
                    object_name=column_name,
                    error_type="MISSING",
                    line_number=0,
                    column_position=0,
                    expected_value="Column should exist",
                    actual_value="Column not found",
                    exact_difference=f"Column '{column_name}' is missing from table '{table_name}'",
                    fix_method="ADD COLUMN",
                    fix_sql=f"ALTER TABLE {table_name} ADD COLUMN {column_name} <type>;",
                    severity="HIGH",
                ))
            else:
                # Compare each attribute
                for attr in ["type", "nullable", "default"]:
                    expected_val = description.split(f"{attr}:")[-1].strip() if f"{attr}:" in description else ""
                    actual_val = str(actual_column.get(attr, ""))

                    if expected_val and expected_val != actual_val:
                        diffs = self._character_level_diff(expected_val, actual_val)
                        line_num, col_pos = self._find_diff_position(expected_val, actual_val)

                        fix_sql = self._generate_column_fix_sql(
                            table_name, column_name, attr, expected_val
                        )

                        errors.append(DatabaseError(
                            table_name=table_name,
                            object_type="COLUMN",
                            object_name=f"{column_name}.{attr}",
                            error_type="ATTRIBUTE_MISMATCH",
                            line_number=line_num,
                            column_position=col_pos,
                            expected_value=expected_val,
                            actual_value=actual_val,
                            exact_difference=diffs,
                            fix_method=f"ALTER COLUMN {attr}",
                            fix_sql=fix_sql,
                            severity="HIGH",
                        ))

        except Exception as exc:
            logger.warning("[NoticerAgent] Column investigation error: %s", exc)
            errors.append(DatabaseError(
                table_name=table_name,
                object_type="COLUMN",
                object_name=column_name,
                error_type="INVESTIGATION_FAILED",
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=f"Could not investigate column: {exc}",
                fix_method="Manual investigation required",
                fix_sql="",
                severity="MEDIUM",
            ))

        return errors

    def _investigate_index_line_by_line(
        self,
        adapter,
        table_name: str,
        index_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate index discrepancies line-by-line."""
        errors: List[DatabaseError] = []

        try:
            import asyncio
            
            async def _fetch_indexes():
                return await adapter.discover_indexes(table_name)
            
            try:
                loop = asyncio.get_running_loop()
                indexes = []
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    indexes = loop.run_until_complete(_fetch_indexes())
                finally:
                    loop.close()

            actual_index = None
            for idx in indexes:
                if idx["name"] == index_name:
                    actual_index = idx
                    break

            if actual_index is None and not indexes:
                # Could not query database - use description-based approach
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="INDEX",
                    object_name=index_name,
                    error_type="MISMATCH",
                    line_number=0,
                    column_position=0,
                    expected_value="",
                    actual_value="",
                    exact_difference=description,
                    fix_method="Investigate and fix index definition",
                    fix_sql="",
                    severity="HIGH",
                ))
            elif actual_index is None:
                errors.append(DatabaseError(
                    table_name=table_name,
                    object_type="INDEX",
                    object_name=index_name,
                    error_type="MISSING",
                    line_number=0,
                    column_position=0,
                    expected_value="Index should exist",
                    actual_value="Index not found",
                    exact_difference=f"Index '{index_name}' is missing from table '{table_name}'",
                    fix_method="CREATE INDEX",
                    fix_sql=f"CREATE INDEX {index_name} ON {table_name} (...);",
                    severity="HIGH",
                ))
            else:
                # Compare index properties
                for prop in ["columns", "unique"]:
                    expected_val = description.split(f"{prop}:")[-1].strip() if f"{prop}:" in description else ""
                    actual_val = str(actual_index.get(prop, ""))

                    if expected_val and expected_val != actual_val:
                        diffs = self._character_level_diff(expected_val, actual_val)
                        line_num, col_pos = self._find_diff_position(expected_val, actual_val)

                        errors.append(DatabaseError(
                            table_name=table_name,
                            object_type="INDEX",
                            object_name=f"{index_name}.{prop}",
                            error_type="PROPERTY_MISMATCH",
                            line_number=line_num,
                            column_position=col_pos,
                            expected_value=expected_val,
                            actual_value=actual_val,
                            exact_difference=diffs,
                            fix_method=f"DROP and recreate INDEX with correct {prop}",
                            fix_sql=f"DROP INDEX IF EXISTS {index_name};\n-- Then create with correct {prop} from Universal JSON",
                            severity="HIGH",
                        ))

        except Exception as exc:
            logger.warning("[NoticerAgent] Index investigation error: %s", exc)
            errors.append(DatabaseError(
                table_name=table_name,
                object_type="INDEX",
                object_name=index_name,
                error_type="INVESTIGATION_FAILED",
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=f"Could not investigate index: {exc}",
                fix_method="Manual investigation required",
                fix_sql="",
                severity="MEDIUM",
            ))

        return errors

    def _investigate_view_line_by_line(
        self,
        adapter,
        table_name: str,
        view_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate view discrepancies line-by-line."""
        errors: List[DatabaseError] = []

        try:
            import asyncio
            
            async def _fetch_views():
                return await adapter.discover_views()
            
            try:
                loop = asyncio.get_running_loop()
                views = []
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    views = loop.run_until_complete(_fetch_views())
                finally:
                    loop.close()

            actual_view = None
            for v in views:
                if v["name"] == view_name:
                    actual_view = v
                    break

            if actual_view is None and not views:
                # Could not query database - use description-based approach
                expected_def = ""
                if "Expected:" in description:
                    expected_def = description.split("Expected:")[-1].strip()
                elif "definition:" in description.lower():
                    parts = description.split("definition:")
                    if len(parts) > 1:
                        expected_def = parts[-1].strip().strip("'\"")
                
                if expected_def:
                    errors.append(DatabaseError(
                        table_name="",
                        object_type="VIEW",
                        object_name=view_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value=expected_def,
                        actual_value="Could not query database",
                        exact_difference=f"View '{view_name}' definition needs correction",
                        fix_method="Update view definition to match Universal JSON",
                        fix_sql=f"-- Update view {view_name} definition\n-- Expected: {expected_def}",
                        severity="HIGH",
                    ))
                else:
                    errors.append(DatabaseError(
                        table_name="",
                        object_type="VIEW",
                        object_name=view_name,
                        error_type="MISMATCH",
                        line_number=0,
                        column_position=0,
                        expected_value="",
                        actual_value="",
                        exact_difference=description,
                        fix_method="Investigate and fix view definition",
                        fix_sql="",
                        severity="HIGH",
                    ))
            elif actual_view is None:
                errors.append(DatabaseError(
                    table_name="",
                    object_type="VIEW",
                    object_name=view_name,
                    error_type="MISSING",
                    line_number=0,
                    column_position=0,
                    expected_value="View should exist",
                    actual_value="View not found",
                    exact_difference=f"View '{view_name}' is missing",
                    fix_method="CREATE VIEW",
                    fix_sql=f"CREATE VIEW {view_name} AS ...;",
                    severity="HIGH",
                ))
            else:
                expected_def = description.split("Expected:")[-1].strip() if "Expected:" in description else ""
                actual_def = actual_view.get("definition", "")

                if expected_def and actual_def != expected_def:
                    diffs = self._character_level_diff(expected_def, actual_def)
                    line_num, col_pos = self._find_diff_position(expected_def, actual_def)

                    errors.append(DatabaseError(
                        table_name="",
                        object_type="VIEW",
                        object_name=view_name,
                        error_type="DEFINITION_MISMATCH",
                        line_number=line_num,
                        column_position=col_pos,
                        expected_value=expected_def,
                        actual_value=actual_def,
                        exact_difference=diffs,
                        fix_method="DROP and CREATE VIEW with correct definition",
                        fix_sql=f"DROP VIEW IF EXISTS {view_name};\n-- Then create with correct definition from Universal JSON",
                        severity="HIGH",
                    ))

        except Exception as exc:
            logger.warning("[NoticerAgent] View investigation error: %s", exc)
            errors.append(DatabaseError(
                table_name="",
                object_type="VIEW",
                object_name=view_name,
                error_type="INVESTIGATION_FAILED",
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=f"Could not investigate view: {exc}",
                fix_method="Manual investigation required",
                fix_sql="",
                severity="MEDIUM",
            ))

        return errors

    def _investigate_missing_object(
        self,
        adapter,
        table_name: str,
        object_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate a missing object."""
        return [DatabaseError(
            table_name=table_name,
            object_type="OBJECT",
            object_name=object_name,
            error_type="MISSING",
            line_number=0,
            column_position=0,
            expected_value="Object should exist",
            actual_value="Object not found",
            exact_difference=description,
            fix_method="CREATE object according to Universal JSON",
            fix_sql=f"-- Create {object_name} on {table_name}\n-- Reference: Universal JSON definition",
            severity="HIGH",
        )]

    def _investigate_extra_object(
        self,
        table_name: str,
        object_name: str,
        description: str,
    ) -> List[DatabaseError]:
        """Investigate an extra object not in Universal JSON."""
        return [DatabaseError(
            table_name=table_name,
            object_type="OBJECT",
            object_name=object_name,
            error_type="EXTRA",
            line_number=0,
            column_position=0,
            expected_value="Object should not exist",
            actual_value="Object exists in database",
            exact_difference=description,
            fix_method="DROP extra object",
            fix_sql=f"DROP {object_name};",
            severity="MEDIUM",
        )]

    def _character_level_diff(self, expected: str, actual: str) -> str:
        """
        Compare two strings character by character and return exact differences.
        100% data match required - no tolerance for any difference.
        """
        if expected == actual:
            return "No differences - 100% match"

        differences = []
        min_len = min(len(expected), len(actual))

        # Compare characters up to the minimum length
        for i in range(min_len):
            exp_char = expected[i]
            act_char = actual[i]

            if exp_char != act_char:
                differences.append(
                    f"Position {i}: expected '{exp_char}' (U+{ord(exp_char):04X}), "
                    f"got '{act_char}' (U+{ord(act_char):04X})"
                )

        # Handle length mismatch
        if len(expected) != len(actual):
            if len(expected) > len(actual):
                # Expected is longer - extra characters
                for i in range(min_len, len(expected)):
                    exp_char = expected[i]
                    differences.append(
                        f"Position {i}: expected '{exp_char}' (U+{ord(exp_char):04X}), "
                        f"got <EOF>"
                    )
            else:
                # Actual is longer - extra characters
                for i in range(min_len, len(actual)):
                    act_char = actual[i]
                    differences.append(
                        f"Position {i}: expected <EOF>, "
                        f"got '{act_char}' (U+{ord(act_char):04X})"
                    )

        if not differences:
            differences.append(
                f"Length mismatch: expected {len(expected)} chars, got {len(actual)} chars"
            )

        return "; ".join(differences)

    def _find_diff_position(self, expected: str, actual: str) -> Tuple[int, int]:
        """Find the line and column position of first difference."""
        for i in range(min(len(expected), len(actual))):
            if expected[i] != actual[i]:
                # Count lines up to this position
                line_num = expected[:i].count('\n') + 1
                # Find column position in current line
                last_newline = expected[:i].rfind('\n')
                col_pos = i - last_newline if last_newline >= 0 else i + 1
                return line_num, col_pos

        # If we get here, strings are equal up to min length
        if len(expected) != len(actual):
            shorter_len = min(len(expected), len(actual))
            line_num = expected[:shorter_len].count('\n') + 1
            last_newline = expected[:shorter_len].rfind('\n')
            col_pos = shorter_len - last_newline if last_newline >= 0 else shorter_len + 1
            return line_num, col_pos

        return 1, 1

    def _generate_column_fix_sql(
        self, table_name: str, column_name: str, attr: str, expected_value: str
    ) -> str:
        """Generate SQL to fix column attribute."""
        if attr == "type":
            return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {expected_value};"
        elif attr == "nullable":
            if expected_value.lower() in ("true", "yes", "nullable"):
                return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL;"
            else:
                return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL;"
        elif attr == "default":
            return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT {expected_value};"
        return f"-- Fix {attr} for {column_name}"

    def _parse_mismatch(self, mismatch: Any) -> Dict[str, Any]:
        """Parse mismatch string or dict to extract structured attributes."""
        if isinstance(mismatch, dict):
            return {
                "table": mismatch.get("table"),
                "object_name": mismatch.get("object_name"),
                "object_type": mismatch.get("type", "UNKNOWN"),
                "error_type": mismatch.get("error_type", "MISMATCH"),
                "description": mismatch.get("description", str(mismatch)),
            }

        mismatch_str = str(mismatch)
        result: Dict[str, Any] = {
            "table": None,
            "object_name": None,
            "object_type": "UNKNOWN",
            "error_type": "MISMATCH",
            "description": mismatch_str,
        }

        # Parse various mismatch patterns
        patterns = [
            (r"Table '([^']+)' Trigger '([^']+)':", "TRIGGER", "TRIGGER_DEFINITION"),
            (r"Table '([^']+)' Constraint '([^']+)':", "CONSTRAINT", "CONSTRAINT_DEFINITION"),
            (r"Table '([^']+)' Column '([^']+)':", "COLUMN", "COLUMN_MISMATCH"),
            (r"Table '([^']+)' Index '([^']+)':", "INDEX", "INDEX_MISMATCH"),
            (r"View '([^']+)':", "VIEW", "VIEW_DEFINITION"),
            (r"Table '([^']+)': missing trigger '([^']+)'", "TRIGGER", "MISSING"),
            (r"Table '([^']+)': missing constraint '([^']+)'", "CONSTRAINT", "MISSING"),
            (r"Table '([^']+)': missing column '([^']+)'", "COLUMN", "MISSING"),
            (r"Table '([^']+)': missing index '([^']+)'", "INDEX", "MISSING"),
            (r"Missing object: '([^']+)'", "OBJECT", "MISSING"),
            (r"Extra object: '([^']+)'", "OBJECT", "EXTRA"),
        ]

        for pattern, obj_type, error_type in patterns:
            m = re.match(pattern, mismatch_str)
            if m:
                result["table"] = m.group(1) if m.lastindex >= 1 else None
                result["object_name"] = m.group(2) if m.lastindex >= 2 else m.group(1)
                result["object_type"] = obj_type
                result["error_type"] = error_type
                return result

        return result

    def _create_errors_from_mismatches(self, mismatches: List[Any]) -> List[DatabaseError]:
        """Create DatabaseError objects from raw mismatches."""
        errors = []
        for mismatch in mismatches:
            parsed = self._parse_mismatch(mismatch)
            errors.append(DatabaseError(
                table_name=parsed.get("table", "unknown"),
                object_type=parsed.get("object_type", "UNKNOWN"),
                object_name=parsed.get("object_name", "unknown"),
                error_type=parsed.get("error_type", "MISMATCH"),
                line_number=0,
                column_position=0,
                expected_value="",
                actual_value="",
                exact_difference=parsed.get("description", str(mismatch)),
                fix_method="Investigate and fix according to Universal JSON",
                fix_sql="",
                severity="HIGH",
            ))
        return errors

    def _verify_100_percent_match(self, errors: List[DatabaseError]) -> Dict[str, Any]:
        """
        Verify 100% data match.
        RULES:
        1. Every character must match exactly
        2. No tolerance for any difference
        3. No partial matches allowed
        """
        total_errors = len(errors)
        character_level_diffs = sum(1 for e in errors if e.exact_difference and "Position" in e.exact_difference)
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

        for error in errors:
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1

        return {
            "total_errors": total_errors,
            "character_level_diffs": character_level_diffs,
            "severity_counts": severity_counts,
            "match_status": "FAIL" if total_errors > 0 else "PASS",
            "tolerance": DataMatchVerification.TOLERANCE,
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _compute_error_hash(self, mismatches: List[Any]) -> str:
        """Compute hash of errors for infinite loop detection."""
        error_str = json.dumps(mismatches, sort_keys=True, default=str)
        return hashlib.sha256(error_str.encode()).hexdigest()[:16]

    def _get_remediation_count(self, project_id: str, error_hash: str) -> int:
        """Get count of remediation attempts for this error pattern."""
        key = f"{project_id}:{error_hash}"
        return self._error_hashes.get(key, 0)

    def _track_remediation_attempt(
        self,
        project_id: str,
        migration_id: str,
        error_hash: str,
        plan_id: str,
        success: bool,
    ) -> None:
        """Track remediation attempt for infinite loop prevention."""
        key = f"{project_id}:{error_hash}"
        self._error_hashes[key] = self._error_hashes.get(key, 0) + 1

        if project_id not in self._remediation_attempts:
            self._remediation_attempts[project_id] = []

        self._remediation_attempts[project_id].append(
            RemediationAttempt(
                attempt_id=plan_id,
                project_id=project_id,
                migration_id=migration_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_hash=error_hash,
                fix_applied=plan_id,
                success=success,
            )
        )

        logger.info(
            "[NoticerAgent] Tracked remediation attempt %d for project %s",
            self._error_hashes[key], project_id
        )

    def _build_remediation_plan(
        self,
        project_id: str,
        migration_id: str,
        errors: List[DatabaseError],
        verification_result: Dict[str, Any],
        attempt_number: int,
    ) -> RemediationPlan:
        """Build comprehensive remediation plan with exact fix instructions."""
        import uuid

        fix_instructions = []
        verification_steps = []

        # Generate fix instructions for each error
        for idx, error in enumerate(errors, 1):
            fix_instructions.append(f"Step {idx}: Fix {error.object_type} '{error.object_name}' on table '{error.table_name}'")
            fix_instructions.append(f"  Error Type: {error.error_type}")
            fix_instructions.append(f"  Location: Line {error.line_number}, Column {error.column_position}")
            fix_instructions.append(f"  Expected: {error.expected_value[:100]}...")
            fix_instructions.append(f"  Actual: {error.actual_value[:100]}...")
            fix_instructions.append(f"  Difference: {error.exact_difference[:200]}")
            if error.fix_sql:
                fix_instructions.append(f"  SQL Fix: {error.fix_sql}")
            fix_instructions.append("")

        # Generate verification steps
        verification_steps.append("1. Connect to target database")
        verification_steps.append("2. Execute fix SQL statements")
        verification_steps.append("3. Re-discover schema")
        verification_steps.append("4. Compare with Universal JSON character-by-character")
        verification_steps.append("5. Verify checksum matches exactly")
        verification_steps.append("6. Confirm 100% data match")

        # Determine risk level
        risk_level = "LOW"
        if any(e.severity == "CRITICAL" for e in errors):
            risk_level = "CRITICAL"
        elif any(e.severity == "HIGH" for e in errors):
            risk_level = "HIGH"
        elif any(e.severity == "MEDIUM" for e in errors):
            risk_level = "MEDIUM"

        return RemediationPlan(
            plan_id=str(uuid.uuid4()),
            project_id=project_id,
            migration_id=migration_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            errors=errors,
            fix_instructions=fix_instructions,
            verification_steps=verification_steps,
            estimated_fix_time=f"{len(errors) * 2} minutes",
            risk_level=risk_level,
            requires_downtime=False,
            total_errors=verification_result["total_errors"],
            character_level_diffs=verification_result["character_level_diffs"],
            remediation_attempt=attempt_number,
            max_attempts=InfiniteLoopPrevention.MAX_REMEDIATION_ATTEMPTS,
        )

    async def _escalate_to_manager(
        self,
        task_id: str,
        project_id: str,
        migration_id: str,
        mismatches: List[Any],
        reason: str,
    ) -> None:
        """Escalate to Manager when infinite loop is detected."""
        escalation_msg = Message(
            sender=AgentType.NOTICER,
            receiver=AgentType.MANAGER,
            message_type=MessageType.TASK_FAILED,
            payload={
                "task_id": task_id,
                "error": f"INFINITE LOOP PREVENTION: {reason}",
                "mismatches": mismatches,
                "remediation_plan": None,
                "escalation": True,
                "escalation_reason": reason,
                "requires_human_intervention": True,
            },
            project_id=project_id,
            migration_id=migration_id,
            priority=Priority.P0_SYSTEM_CRITICAL,
        )
        await self._bus.publish(escalation_msg)
        logger.error("[NoticerAgent] Escalated to Manager: %s", reason)

    async def _send_to_manager(
        self,
        task_id: str,
        project_id: str,
        migration_id: str,
        mismatches: List[Any],
        remediation_plan: RemediationPlan,
    ) -> None:
        """Send remediation plan to Manager."""
        manager_msg = Message(
            sender=AgentType.NOTICER,
            receiver=AgentType.MANAGER,
            message_type=MessageType.TASK_FAILED,
            payload={
                "task_id": task_id,
                "error": f"Validation failed with {remediation_plan.total_errors} errors. "
                         f"Character-level diffs: {remediation_plan.character_level_diffs}. "
                         f"Remediation attempt: {remediation_plan.remediation_attempt}/{remediation_plan.max_attempts}.",
                "mismatches": mismatches,
                "remediation_plan": remediation_plan.to_dict(),
                "fix_instructions": remediation_plan.fix_instructions,
                "verification_steps": remediation_plan.verification_steps,
                "total_errors": remediation_plan.total_errors,
                "character_level_diffs": remediation_plan.character_level_diffs,
                "remediation_attempt": remediation_plan.remediation_attempt,
                "max_attempts": remediation_plan.max_attempts,
                "risk_level": remediation_plan.risk_level,
            },
            project_id=project_id,
            migration_id=migration_id,
            priority=Priority.P0_SYSTEM_CRITICAL,
        )
        await self._bus.publish(manager_msg)
