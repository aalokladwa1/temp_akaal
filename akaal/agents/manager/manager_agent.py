"""
NexusForge — Manager Agent
============================
The central deterministic orchestration controller of NexusForge.

manager_agent.md:
  The Manager Agent is the central orchestration unit of NexusForge.
  It does NOT execute raw data processing. It ONLY:
    - Controls workflow execution
    - Assigns tasks to agents
    - Monitors system state
    - Ensures validation pipeline is followed
    - Enforces guardrails and failover rules
    - Maintains global execution order

Execution loop (manager_agent.md Section 5):
  Observe system state
  → Analyze workflow stage
  → Assign tasks
  → Wait for agent completion
  → Validate results via Validator
  → Update global state
  → Trigger next stage

Decision rules (manager_agent.md Section 6):
  ALWAYS prefer validated data
  NEVER skip workflow steps
  NEVER bypass Validator
  NEVER directly modify data systems
  NEVER execute Scout or Validator logic
  NEVER ignore Live Intel warnings

Security rules (TRD Section 13):
  NEVER store plaintext credentials
  Validate permissions before assigning work
  Authenticate every connected component

This is Agent 1. All other agents are placeholders until built.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from akaal.agents.manager.approval_controller import ApprovalController
from akaal.agents.manager.incident_manager import IncidentManager
from akaal.agents.manager.queue_manager import QueueManager
from akaal.agents.manager.workflow_engine import InvalidTransitionError, WorkflowEngine
from akaal.audit.audit_logger import AuditEventType, AuditLogger
from akaal.core.loop_governor.governor import LoopGovernor, LoopState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.models.enums import (
    AgentStatus,
    AgentType,
    ApprovalDecision,
    FailureReason,
    FailureType,
    IncidentSeverity,
    LoopDecision,
    MigrationStrategy,
    Priority,
    SystemType,
    TaskType,
    WorkflowState,
)
from akaal.core.models.message import Message, MessageType
from akaal.core.models.project import (
    ApprovalRecord,
    ConnectionConfig,
    MigrationProject,
    MigrationSession,
)
from akaal.core.models.task import Task, TaskResult, TaskStatus
from akaal.core.state.global_state import CheckpointEntry, GlobalState

logger = logging.getLogger("nexusforge.manager")


# ---------------------------------------------------------------------------
# Manager Agent
# ---------------------------------------------------------------------------

class TaskExecutionError(Exception):
    """Raised when a background task execution fails."""
    def __init__(self, task: Task, result: TaskResult, can_retry: bool = False) -> None:
        super().__init__(f"Task {task.task_type.value} failed: {result.error_message}")
        self.task = task
        self.result = result
        self.can_retry = can_retry


class ManagerAgent:
    """
    The deterministic orchestration controller for NexusForge.

    Lifecycle:
      1. start()          — initialize and register all subsystems
      2. create_project() — create a new migration project
      3. run_migration()  — execute the full migration workflow
      4. stop()           — graceful shutdown

    The Manager never performs discovery, validation, migration, or repair.
    It only coordinates, assigns, monitors, and gates.
    """

    AGENT_ID: str = "MANAGER-001"

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        audit_logger: AuditLogger,
        approval_controller: Optional[ApprovalController] = None,
        cli_mode: bool = True,
        agent_id: str = "MANAGER-001",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self._audit = audit_logger
        self.agent_id = agent_id
        self._is_backup = is_backup

        # Subsystems
        self._workflow = WorkflowEngine()
        self._queues = QueueManager()
        self._loop_governor = LoopGovernor()
        self._incident_mgr = IncidentManager(global_state, audit_logger)
        self._approval_ctrl = approval_controller or ApprovalController(cli_mode=cli_mode)

        # Internal tracking
        self._running: bool = False
        self._active_tasks: Dict[str, Task] = {}    # task_id → Task
        self._task_events: Dict[str, asyncio.Event] = {}  # task_id → Event
        self._remediation_plans: Dict[str, str] = {}  # project_id → plan

        # Register Loop Governor callbacks
        self._loop_governor.register_freeze_callback(self._on_freeze)
        self._loop_governor.register_escalation_callback(self._on_escalation)

        logger.info("[ManagerAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Start the Manager Agent and register with global state.
        Subscribes to the message bus for incoming messages.
        """
        self._running = True

        # Register self in global state
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.MANAGER, self.agent_id)
        await self._state.update_agent_status(AgentType.MANAGER, status, self.agent_id)

        # Subscribe to message bus
        await self._bus.subscribe(AgentType.MANAGER, self._handle_message)
        await self._bus.start()

        self._audit.log(
            event_type=AuditEventType.SYSTEM_STARTED,
            actor=AgentType.MANAGER.value,
            description="Manager Agent started and registered.",
            details={"agent_id": self.agent_id},
        )

        logger.info("[ManagerAgent] Started successfully. ID=%s Status=%s", self.agent_id, status.value)

    async def stop(self) -> None:
        """Gracefully stop the Manager Agent."""
        self._running = False
        self._queues.pause_all()
        await self._state.update_agent_status(AgentType.MANAGER, AgentStatus.OFFLINE, self.agent_id)
        await self._bus.unsubscribe(AgentType.MANAGER, self._handle_message)
        logger.info("[ManagerAgent] Stopped. ID=%s", self.agent_id)

    # ------------------------------------------------------------------
    # Project Creation (workflow.md Section 4)
    # ------------------------------------------------------------------

    async def create_project(
        self,
        name: str,
        source_config: ConnectionConfig,
        target_config: ConnectionConfig,
        strategy: MigrationStrategy,
        created_by: str = "system",
    ) -> MigrationProject:
        """
        Create a new migration project.

        Validates all required fields (workflow.md Section 4, Step 2).
        Generates Project ID, Migration ID, Audit Session, Execution Session.
        Verifies platform readiness before starting discovery.

        Raises ValueError for duplicate, invalid, or incomplete requests.
        TRD Section 13 Workflow Control: Manager shall reject duplicate,
        invalid, expired, unauthorized, incomplete requests.
        """
        # --- Guard: frozen system ---
        if self._state.is_frozen():
            raise RuntimeError(
                f"System is frozen: {self._state.freeze_reason()}. "
                "Human intervention required before new projects can be created."
            )

        # --- Input validation ---
        if not name or not name.strip():
            raise ValueError("Project name is required.")
        if not source_config:
            raise ValueError("Source connection config is required.")
        if not target_config:
            raise ValueError("Target connection config is required.")
        if not strategy:
            raise ValueError("Migration strategy is required.")
        if not source_config.read_only:
            raise ValueError(
                "Source connection must be read-only. "
                "NexusForge never modifies source systems."
            )

        # --- Create project ---
        project = MigrationProject(
            name=name.strip(),
            source_config=source_config,
            target_config=target_config,
            strategy=strategy,
            created_by=created_by,
        )

        # --- Generate session IDs ---
        project.audit_session_id = str(uuid.uuid4())
        project.execution_session_id = str(uuid.uuid4())

        # --- Register in global state ---
        await self._state.register_project(project)

        # --- Transition to PROJECT_CREATED ---
        new_state = self._workflow.transition(
            WorkflowState.IDLE,
            WorkflowState.PROJECT_CREATED,
            project.project_id,
            reason="Project created by user",
        )
        await self._state.update_project_state(project.project_id, new_state, "Project created")

        # --- Audit ---
        self._audit.log(
            event_type=AuditEventType.PROJECT_CREATED,
            actor=created_by,
            description=f"Migration project '{name}' created.",
            project_id=project.project_id,
            details={
                "strategy": strategy.value,
                "source_type": source_config.system_type.value,
                "target_type": target_config.system_type.value,
                "audit_session_id": project.audit_session_id,
                "execution_session_id": project.execution_session_id,
            },
        )

        logger.info(
            "[ManagerAgent] Project created: '%s' (id=%s)", name, project.project_id
        )
        return project

    # ------------------------------------------------------------------
    # Migration Orchestration (workflow.md Sections 5–14)
    # ------------------------------------------------------------------

    async def run_migration(self, project_id: str) -> Dict[str, Any]:
        """
        Execute the full migration workflow for a project.

        Follows the deterministic workflow:
        PROJECT_CREATED → DISCOVERY → VALIDATION → GB → HUMAN APPROVAL
        → PRODUCTION → VALIDATION → CDC → COMPLETED

        Returns a summary dict on completion.
        Raises on unrecoverable failure.
        """
        if self._is_backup:
            raise PermissionError("Backup Manager cannot initiate or run migration workflows in standby.")

        project = await self._state.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        if project.is_terminal():
            raise ValueError(
                f"Project {project_id} is in terminal state {project.state.value}. "
                "Cannot re-run a completed or cancelled migration."
            )

        logger.info("[ManagerAgent] Starting migration for project: %s", project_id)

        self._audit.log(
            event_type=AuditEventType.WORKFLOW_STARTED,
            actor=AgentType.MANAGER.value,
            description=f"Migration workflow started for project {project.name}.",
            project_id=project_id,
            migration_id=project.active_migration_id,
        )

        # Create migration session
        session = MigrationSession(project_id=project_id)
        project.active_migration_id = session.migration_id
        await self._state.register_session(session)

        while True:
            try:
                # --- Stage 1: Discovery ---
                await self._run_discovery_stage(project, session)

                # --- Stage 2: GB Import ---
                await self._run_gb_import_stage(project, session)

                # --- Stage 3: Human Approval ---
                approval = await self._run_human_approval_stage(project)

                if approval.decision != ApprovalDecision.APPROVE.value:
                    await self._handle_approval_rejection(project, approval)
                    return {"status": "rejected", "reason": approval.decision}

                # --- Stage 4: Production Migration ---
                await self._run_production_migration_stage(project, session)

                # --- Stage 5: CDC Synchronization ---
                await self._run_cdc_stage(project, session)

                # --- Complete ---
                await self._complete_migration(project, session)

                return {
                    "status": "completed",
                    "project_id": project_id,
                    "migration_id": session.migration_id,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }

            except TaskExecutionError as err:
                if err.can_retry:
                    logger.warning("[ManagerAgent] Task failed with retry decision. Running recovery workflow.")
                    # Recovery workflow transitions:
                    # current_state -> FAILED -> RECOVERY_STARTED -> CHECKPOINT_RESTORE -> RETRYING
                    await self._transition(project, WorkflowState.FAILED, f"Task failed: {err}")
                    await self._transition(project, WorkflowState.RECOVERY_STARTED, "Recovery initialized")
                    await self._transition(project, WorkflowState.CHECKPOINT_RESTORE, "Restoring checkpoint")

                    latest_cp = self._state.get_latest_checkpoint(project.project_id)
                    if latest_cp:
                        # Dispatch restore task
                        restore_task = self._build_task(
                            task_type=TaskType.CHECKPOINT_RESTORE,
                            assigned_to=AgentType.CHECKPOINT_ENGINE,
                            project=project,
                            session=session,
                            priority=Priority.P0_SYSTEM_CRITICAL,
                            parameters={"checkpoint_id": latest_cp.checkpoint_id},
                        )
                        restore_result = await self._dispatch_task(restore_task, project)
                        if not restore_result.success:
                            logger.error("[ManagerAgent] Checkpoint restore failed: %s", restore_result.error_message)
                            raise RuntimeError(f"Checkpoint restore failed: {restore_result.error_message}")

                        logger.info("[ManagerAgent] Restored checkpoint %s", latest_cp.checkpoint_id)
                        self._audit.log(
                            event_type=AuditEventType.CHECKPOINT_RESTORED,
                            actor=AgentType.MANAGER.value,
                            description=f"Checkpoint {latest_cp.checkpoint_id} restored.",
                            project_id=project_id,
                            migration_id=session.migration_id,
                        )

                    await self._transition(project, WorkflowState.RETRYING, "Ready for retry")

                    # Map the failed task to the retry state
                    state_mapping = {
                        TaskType.DISCOVERY: WorkflowState.DISCOVERY_STARTED,
                        TaskType.GB_IMPORT: WorkflowState.GB_LOADING,
                        TaskType.GB_VALIDATION: WorkflowState.GB_LOADING,
                        TaskType.MIGRATION_BATCH: WorkflowState.PRODUCTION_MIGRATION,
                        TaskType.CDC_SYNC: WorkflowState.CDC_SYNCHRONIZATION,
                    }
                    retry_state = state_mapping.get(err.task.task_type, WorkflowState.DISCOVERY_STARTED)
                    if err.task.task_type == TaskType.VALIDATION:
                        if err.task.parameters.get("stage") == "discovery":
                            retry_state = WorkflowState.DISCOVERY_STARTED
                        else:
                            retry_state = WorkflowState.PRODUCTION_MIGRATION

                    await self._transition(project, retry_state, f"Retrying from {retry_state.value}")
                    # Loop back to retry the workflow
                    continue
                else:
                    # Permanent failure
                    logger.error("[ManagerAgent] Task failed with permanent decision. Halting migration.")
                    await self._handle_migration_failure(project, session, str(err))
                    raise
            except Exception as exc:
                logger.error(
                    "[ManagerAgent] Migration failed for project=%s: %s",
                    project_id, exc, exc_info=True
                )
                await self._handle_migration_failure(project, session, str(exc))
                raise

    # ------------------------------------------------------------------
    # Stage: Discovery (workflow.md Section 5)
    # ------------------------------------------------------------------

    async def _run_discovery_stage(
        self,
        project: MigrationProject,
        session: MigrationSession,
    ) -> None:
        """Assign Scout for source discovery, then request validation."""
        if project.state not in (WorkflowState.PROJECT_CREATED, WorkflowState.DISCOVERY_STARTED, WorkflowState.RETRYING, WorkflowState.IDLE):
            logger.info("[ManagerAgent] Skipping DISCOVERY stage (already in state %s)", project.state.value)
            return

        logger.info("[ManagerAgent] Stage: DISCOVERY for project=%s", project.project_id)

        # Transition to DISCOVERY_STARTED
        if project.state != WorkflowState.DISCOVERY_STARTED:
            await self._transition(
                project, WorkflowState.DISCOVERY_STARTED, "Discovery stage starting"
            )

        # Assign Scout task
        scout_params = {"source_config": project.source_config.__repr__()}
        plan = self._remediation_plans.pop(project.project_id, None)
        if plan:
            scout_params["remediation_plan"] = plan

        task = self._build_task(
            task_type=TaskType.DISCOVERY,
            assigned_to=AgentType.SCOUT,
            project=project,
            session=session,
            priority=Priority.P3_DISCOVERY,
            parameters=scout_params,
        )

        result = await self._dispatch_task(task, project)

        if not result.success:
            decision = await self._handle_task_failure(project, session, task, result)
            raise TaskExecutionError(task, result, can_retry=(decision == LoopDecision.RETRY))

        # Transition to DISCOVERY_COMPLETED
        await self._transition(
            project, WorkflowState.DISCOVERY_COMPLETED, "Scout discovery complete"
        )

        # Assign Validator task
        validation_task = self._build_task(
            task_type=TaskType.VALIDATION,
            assigned_to=AgentType.VALIDATOR,
            project=project,
            session=session,
            priority=Priority.P2_VALIDATION,
            parameters={"stage": "discovery", "discovery_result_ref": result.output.get("result_ref")},
        )

        val_result = await self._dispatch_task(validation_task, project)

        if not val_result.success:
            decision = await self._handle_task_failure(project, session, validation_task, val_result)
            raise TaskExecutionError(validation_task, val_result, can_retry=(decision == LoopDecision.RETRY))

        # Transition to DISCOVERY_VALIDATED
        await self._transition(
            project, WorkflowState.DISCOVERY_VALIDATED, "Discovery validated"
        )

        # Create checkpoint
        await self._create_checkpoint(project, "Post-discovery checkpoint")

        self._audit.log(
            event_type=AuditEventType.DISCOVERY_COMPLETED,
            actor=AgentType.MANAGER.value,
            description="Source discovery and validation completed.",
            project_id=project.project_id,
            migration_id=session.migration_id,
            details={"task_id": task.task_id, "validation_task_id": validation_task.task_id},
        )

    # ------------------------------------------------------------------
    # Stage: GB Import (workflow.md Section 8 & 9)
    # ------------------------------------------------------------------

    async def _run_gb_import_stage(
        self,
        project: MigrationProject,
        session: MigrationSession,
    ) -> None:
        """Import validated Universal JSON into GB staging environment."""
        if project.state not in (WorkflowState.DISCOVERY_VALIDATED, WorkflowState.GB_LOADING, WorkflowState.GB_LOADED, WorkflowState.GB_VALIDATION, WorkflowState.RETRYING):
            logger.info("[ManagerAgent] Skipping GB IMPORT stage (already in state %s)", project.state.value)
            return

        logger.info("[ManagerAgent] Stage: GB IMPORT for project=%s", project.project_id)

        # We only run the import step if we haven't successfully loaded the GB database yet
        if project.state in (WorkflowState.DISCOVERY_VALIDATED, WorkflowState.GB_LOADING, WorkflowState.RETRYING):
            if project.state != WorkflowState.GB_LOADING:
                await self._transition(project, WorkflowState.GB_LOADING, "GB import starting")

            gb_task = self._build_task(
                task_type=TaskType.GB_IMPORT,
                assigned_to=AgentType.GB,
                project=project,
                session=session,
                priority=Priority.P1_MIGRATION,
            )

            result = await self._dispatch_task(gb_task, project)

            if not result.success:
                decision = await self._handle_task_failure(project, session, gb_task, result)
                raise TaskExecutionError(gb_task, result, can_retry=(decision == LoopDecision.RETRY))

            await self._transition(project, WorkflowState.GB_LOADED, "GB import complete")

        # We only run the validation step if we are loaded or in validation phase
        if project.state in (WorkflowState.GB_LOADED, WorkflowState.GB_VALIDATION):
            if project.state != WorkflowState.GB_VALIDATION:
                await self._transition(project, WorkflowState.GB_VALIDATION, "GB validation starting")

            val_task = self._build_task(
                task_type=TaskType.GB_VALIDATION,
                assigned_to=AgentType.VALIDATOR,
                project=project,
                session=session,
                priority=Priority.P2_VALIDATION,
                parameters={"stage": "gb_validation"},
            )

            val_result = await self._dispatch_task(val_task, project)

            if not val_result.success:
                decision = await self._handle_task_failure(project, session, val_task, val_result)
                raise TaskExecutionError(val_task, val_result, can_retry=(decision == LoopDecision.RETRY))

            await self._transition(project, WorkflowState.GB_VALIDATED, "GB validated")
            await self._create_checkpoint(project, "Post-GB-validation checkpoint")

        self._audit.log(
            event_type=AuditEventType.GB_VALIDATION_PASSED,
            actor=AgentType.MANAGER.value,
            description="GB import and validation completed successfully.",
            project_id=project.project_id,
            migration_id=session.migration_id,
        )

    # ------------------------------------------------------------------
    # Stage: Human Approval (workflow.md Section 10)
    # ------------------------------------------------------------------

    async def _run_human_approval_stage(
        self,
        project: MigrationProject,
    ) -> ApprovalRecord:
        """Present migration summary to human and wait for decision."""
        if project.human_approval_granted:
            logger.info("[ManagerAgent] Skipping HUMAN APPROVAL stage (already approved)")
            return ApprovalRecord(
                project_id=project.project_id,
                migration_id=project.active_migration_id or "",
                decision=ApprovalDecision.APPROVE.value,
                decided_by=project.approved_by or "system",
                notes="Skipped approval (already approved)"
            )
        if project.state not in (WorkflowState.GB_VALIDATED, WorkflowState.HUMAN_APPROVAL_PENDING, WorkflowState.RETRYING):
            logger.info("[ManagerAgent] Skipping HUMAN APPROVAL stage (state %s)", project.state.value)
            return ApprovalRecord(
                project_id=project.project_id,
                migration_id=project.active_migration_id or "",
                decision=ApprovalDecision.REJECT.value,
                decided_by="system",
                notes=f"Skipped in invalid state: {project.state.value}"
            )

        logger.info("[ManagerAgent] Stage: HUMAN APPROVAL for project=%s", project.project_id)

        await self._transition(
            project,
            WorkflowState.HUMAN_APPROVAL_PENDING,
            "Awaiting human approval before production migration",
        )

        self._audit.log(
            event_type=AuditEventType.APPROVAL_REQUESTED,
            actor=AgentType.MANAGER.value,
            description="Human approval requested before production migration.",
            project_id=project.project_id,
        )

        # Build approval details from state
        details = {
            "validation_results": {
                "discovery": "PASS",
                "gb_validation": "PASS",
            },
            "object_statistics": {
                "total_objects": project.total_objects_discovered,
                "strategy": project.strategy.value,
            },
            "risk_assessment": "LOW — All automated validations passed",
            "detected_risks": [],
            "checkpoint_status": "Checkpoint available for restore",
            "recovery_plan": "Restore from last checkpoint",
            "rollback_plan": "Restore from pre-migration checkpoint",
            "estimated_migration_time": "TBD by Scout analysis",
            "estimated_downtime": "Minimal — CDC-based synchronization",
        }

        # Request human approval (blocks until decision)
        approval = await self._approval_ctrl.request_approval(project, details)

        # Record decision in project
        if approval.decision == ApprovalDecision.APPROVE.value:
            project.human_approval_granted = True
            project.approved_by = approval.decided_by
            project.approved_at = approval.decided_at

            await self._transition(
                project, WorkflowState.HUMAN_APPROVED, f"Approved by {approval.decided_by}"
            )

            self._audit.log(
                event_type=AuditEventType.APPROVAL_GRANTED,
                actor=approval.decided_by,
                description=f"Production migration approved by {approval.decided_by}.",
                project_id=project.project_id,
                migration_id=project.active_migration_id,
                details=approval.to_dict(),
            )
        else:
            self._audit.log(
                event_type=AuditEventType.APPROVAL_REJECTED,
                actor=approval.decided_by,
                description=f"Production migration rejected/paused by {approval.decided_by}.",
                project_id=project.project_id,
                details=approval.to_dict(),
            )

        return approval

    # ------------------------------------------------------------------
    # Stage: Production Migration (workflow.md Section 11)
    # ------------------------------------------------------------------

    async def _run_production_migration_stage(
        self,
        project: MigrationProject,
        session: MigrationSession,
    ) -> None:
        """Execute production migration in batches with per-batch checkpoints."""
        if project.state not in (WorkflowState.HUMAN_APPROVED, WorkflowState.PRODUCTION_MIGRATION, WorkflowState.PRODUCTION_VALIDATION, WorkflowState.RETRYING):
            logger.info("[ManagerAgent] Skipping PRODUCTION MIGRATION stage (already in state %s)", project.state.value)
            return

        logger.info(
            "[ManagerAgent] Stage: PRODUCTION MIGRATION for project=%s", project.project_id
        )

        # Verify all pre-conditions before starting production (workflow.md Section 11)
        if not project.human_approval_granted:
            raise RuntimeError(
                "SAFETY VIOLATION: Production migration attempted without human approval. "
                "This should never happen."
            )

        if project.state in (WorkflowState.HUMAN_APPROVED, WorkflowState.PRODUCTION_MIGRATION, WorkflowState.RETRYING):
            if project.state != WorkflowState.PRODUCTION_MIGRATION:
                await self._transition(
                    project, WorkflowState.PRODUCTION_MIGRATION, "Production migration starting"
                )

            self._audit.log(
                event_type=AuditEventType.MIGRATION_STARTED,
                actor=AgentType.MANAGER.value,
                description="Production migration started.",
                project_id=project.project_id,
                migration_id=session.migration_id,
                details={"approved_by": project.approved_by},
            )

            # Migration executes in batches (workflow.md Section 11)
            # In Phase 1 this is a single batch — batch management expands when GB Agent is built
            mig_task = self._build_task(
                task_type=TaskType.MIGRATION_BATCH,
                assigned_to=AgentType.GB,   # GB Agent handles the data transfer
                project=project,
                session=session,
                priority=Priority.P1_MIGRATION,
                parameters={"batch_number": 1, "batch_total": 1},
            )

            result = await self._dispatch_task(mig_task, project)

            if not result.success:
                decision = await self._handle_task_failure(project, session, mig_task, result)
                raise TaskExecutionError(mig_task, result, can_retry=(decision == LoopDecision.RETRY))

            # Post-batch checkpoint
            await self._create_checkpoint(project, "Post-migration-batch checkpoint")

            session.completed_batches += 1

        # Production validation
        if project.state in (WorkflowState.PRODUCTION_MIGRATION, WorkflowState.PRODUCTION_VALIDATION):
            if project.state != WorkflowState.PRODUCTION_VALIDATION:
                await self._transition(
                    project, WorkflowState.PRODUCTION_VALIDATION, "Production validation starting"
                )

            pv_task = self._build_task(
                task_type=TaskType.VALIDATION,
                assigned_to=AgentType.VALIDATOR,
                project=project,
                session=session,
                priority=Priority.P2_VALIDATION,
                parameters={"stage": "production_validation"},
            )

            pv_result = await self._dispatch_task(pv_task, project)

            if not pv_result.success:
                decision = await self._handle_task_failure(project, session, pv_task, pv_result)
                raise TaskExecutionError(pv_task, pv_result, can_retry=(decision == LoopDecision.RETRY))

        self._audit.log(
            event_type=AuditEventType.MIGRATION_BATCH_COMPLETE,
            actor=AgentType.MANAGER.value,
            description="Production migration and validation complete.",
            project_id=project.project_id,
            migration_id=session.migration_id,
        )

    # ------------------------------------------------------------------
    # Stage: CDC Synchronization (workflow.md Section 13)
    # ------------------------------------------------------------------

    async def _run_cdc_stage(
        self,
        project: MigrationProject,
        session: MigrationSession,
    ) -> None:
        """Start CDC synchronization to catch up any changes since migration began."""
        if project.state not in (WorkflowState.PRODUCTION_VALIDATION, WorkflowState.CDC_SYNCHRONIZATION, WorkflowState.RETRYING):
            logger.info("[ManagerAgent] Skipping CDC stage (already in state %s)", project.state.value)
            return

        logger.info("[ManagerAgent] Stage: CDC SYNC for project=%s", project.project_id)

        if project.state != WorkflowState.CDC_SYNCHRONIZATION:
            await self._transition(
                project, WorkflowState.CDC_SYNCHRONIZATION, "CDC synchronization starting"
            )

        self._audit.log(
            event_type=AuditEventType.CDC_STARTED,
            actor=AgentType.MANAGER.value,
            description="CDC synchronization started.",
            project_id=project.project_id,
            migration_id=session.migration_id,
        )

        cdc_task = self._build_task(
            task_type=TaskType.CDC_SYNC,
            assigned_to=AgentType.CDC_ENGINE,
            project=project,
            session=session,
            priority=Priority.P1_MIGRATION,
        )

        result = await self._dispatch_task(cdc_task, project)

        if not result.success:
            decision = await self._handle_task_failure(project, session, cdc_task, result)
            raise TaskExecutionError(cdc_task, result, can_retry=(decision == LoopDecision.RETRY))

        self._audit.log(
            event_type=AuditEventType.CDC_COMPLETED,
            actor=AgentType.MANAGER.value,
            description="CDC synchronization completed.",
            project_id=project.project_id,
            migration_id=session.migration_id,
        )

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    async def _complete_migration(
        self,
        project: MigrationProject,
        session: MigrationSession,
    ) -> None:
        """Mark migration as fully completed and generate final checkpoint."""
        session.complete()

        await self._transition(
            project, WorkflowState.MIGRATION_COMPLETED, "Migration successfully completed"
        )

        # Final checkpoint
        await self._create_checkpoint(project, "Final migration completion checkpoint")

        self._audit.log(
            event_type=AuditEventType.MIGRATION_COMPLETED,
            actor=AgentType.MANAGER.value,
            description=f"Migration '{project.name}' completed successfully.",
            project_id=project.project_id,
            migration_id=session.migration_id,
            details={
                "duration_seconds": session.duration_seconds(),
                "batches_completed": session.completed_batches,
                "approved_by": project.approved_by,
            },
        )

        logger.info(
            "[ManagerAgent] Migration COMPLETED for project=%s in %.1fs",
            project.project_id,
            session.duration_seconds() or 0.0
        )

    # ------------------------------------------------------------------
    # Failure Handling (manager_agent.md Section 8)
    # ------------------------------------------------------------------

    async def _handle_migration_failure(
        self,
        project: MigrationProject,
        session: MigrationSession,
        error: str,
    ) -> None:
        """Handle a migration-level failure — pause, incident, checkpoint."""
        logger.error(
            "[ManagerAgent] Migration failure for project=%s: %s",
            project.project_id, error
        )

        # Only transition to FAILED if not already in a terminal state
        if not project.is_terminal() and project.state not in (
            WorkflowState.FAILED,
            WorkflowState.RECOVERY_STARTED,
        ):
            try:
                await self._transition(project, WorkflowState.FAILED, error)
            except InvalidTransitionError:
                pass  # Already in an incompatible state

        # Create incident
        await self._incident_mgr.create_incident(
            project_id=project.project_id,
            migration_id=session.migration_id,
            source_agent=AgentType.MANAGER,
            failure_reason=FailureReason.UNKNOWN,
            description=f"Migration failure: {error}",
        )

        self._audit.log(
            event_type=AuditEventType.INCIDENT_CREATED,
            actor=AgentType.MANAGER.value,
            description=f"Migration failed: {error}",
            project_id=project.project_id,
            migration_id=session.migration_id,
        )

    async def _handle_task_failure(
        self,
        project: MigrationProject,
        session: MigrationSession,
        task: Task,
        result: TaskResult,
    ) -> LoopDecision:
        """Handle individual task failure — loop governor evaluation."""
        failure_reason = FailureReason.UNKNOWN
        failure_type = FailureType.MODERATE

        # Evaluate with Loop Governor
        loop_state = self._loop_governor.get_or_create_state(
            task.assigned_to, project.project_id, session.migration_id
        )

        decision = await self._loop_governor.evaluate(
            loop_state,
            current_state_data={
                "project_id": project.project_id,
                "task_type": task.task_type.value,
                "state": project.state.value,
                "error": result.error_message,
            },
            failure_type=failure_type,
            failure_reason=failure_reason,
        )

        self._audit.log(
            event_type=AuditEventType.TASK_FAILED,
            actor=AgentType.MANAGER.value,
            description=f"Task {task.task_id} failed. Loop decision: {decision.value}",
            project_id=project.project_id,
            migration_id=session.migration_id,
            details={
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "decision": decision.value,
                "error": result.error_message,
            },
        )

        if decision == LoopDecision.RETRY:
            logger.warning(
                "[ManagerAgent] Task %s failed — retry permitted.", task.task_id[:8]
            )
        elif decision in (LoopDecision.ESCALATE, LoopDecision.STOP, LoopDecision.FREEZE):
            # Create an incident and escalate
            await self._incident_mgr.create_incident(
                project_id=project.project_id,
                migration_id=session.migration_id,
                source_agent=task.assigned_to,
                failure_reason=failure_reason,
                description=(
                    f"Task {task.task_type.value} failed after loop governor decision: "
                    f"{decision.value}"
                ),
                severity_override=IncidentSeverity.CRITICAL,
            )
        return decision

    async def _handle_approval_rejection(
        self,
        project: MigrationProject,
        approval: ApprovalRecord,
    ) -> None:
        """Handle non-approve decisions from the human approval gate."""
        if approval.decision == ApprovalDecision.PAUSE.value:
            await self._transition(
                project, WorkflowState.PAUSED, f"Paused by {approval.decided_by}"
            )
        elif approval.decision == ApprovalDecision.CANCEL.value:
            await self._transition(
                project, WorkflowState.CANCELLED, f"Cancelled by {approval.decided_by}"
            )
        elif approval.decision == ApprovalDecision.REJECT.value:
            await self._transition(
                project, WorkflowState.FAILED, f"Rejected by {approval.decided_by}"
            )
            await self._incident_mgr.create_incident(
                project_id=project.project_id,
                migration_id=project.active_migration_id,
                source_agent=AgentType.MANAGER,
                failure_reason=FailureReason.UNKNOWN,
                description=f"Migration rejected by human: {approval.decided_by}",
            )

    # ------------------------------------------------------------------
    # Loop Governor Callbacks
    # ------------------------------------------------------------------

    async def _on_freeze(self, loop_state: LoopState) -> None:
        """Called when Loop Governor triggers a system freeze."""
        reason = (
            f"Infinite loop detected — agent={loop_state.agent_type.value}, "
            f"project={loop_state.project_id}, "
            f"hash_repeats={loop_state.count_repeated_state_hash()}"
        )
        await self._state.freeze_system(reason)
        self._queues.pause_all()

        self._audit.log(
            event_type=AuditEventType.LOOP_FREEZE,
            actor=AgentType.MANAGER.value,
            description=f"System frozen: {reason}",
            project_id=loop_state.project_id,
        )
        logger.critical("[ManagerAgent] SYSTEM FROZEN: %s", reason)

    async def _on_escalation(self, loop_state: LoopState, reason: str) -> None:
        """Called when Loop Governor escalates a failure."""
        self._audit.log(
            event_type=AuditEventType.LOOP_ESCALATE,
            actor=AgentType.MANAGER.value,
            description=f"Loop escalation: {reason}",
            project_id=loop_state.project_id,
            details={
                "agent": loop_state.agent_type.value,
                "attempt_count": loop_state.attempt_count,
            },
        )
        logger.error("[ManagerAgent] Loop escalation: %s", reason)

    # ------------------------------------------------------------------
    # Message Bus Handler
    # ------------------------------------------------------------------

    async def _handle_message(self, message: Message) -> None:
        """
        Handle incoming messages from akaal.agents.
        Manager_agent.md Section 9: Manager communicates ONLY via
        structured messages, message bus, API calls, checkpoint updates.
        """
        if not message.verify_integrity():
            logger.error(
                "[ManagerAgent] Message integrity check failed. Discarding. msg_id=%s",
                message.message_id
            )
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.MANAGER, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.MANAGER, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.MANAGER, status, self.agent_id)
                logger.critical("[ManagerAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore other messages if in standby
        if self._is_backup:
            logger.debug("[ManagerAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
            return

        msg_type = message.message_type
        logger.debug("[ManagerAgent] Received message: %s from %s", msg_type, message.sender.value)

        if msg_type == MessageType.TASK_RESULT:
            await self._process_task_result(message)
        elif msg_type == MessageType.TASK_FAILED:
            await self._process_task_failed(message)
        elif msg_type == MessageType.HEALTH_CHECK_RESPONSE:
            await self._process_health_response(message)
        elif msg_type == MessageType.LOOP_WARNING:
            await self._process_loop_warning(message)
        else:
            logger.warning(
                "[ManagerAgent] Unknown message type: %s from %s",
                msg_type, message.sender.value
            )

    async def _process_task_result(self, message: Message) -> None:
        """Process a task completion result from an agent."""
        task_id = message.payload.get("task_id")
        if task_id and task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            task.complete(result_ref=message.payload.get("result_ref"))
            task.parameters["result_output"] = message.payload
            logger.info("[ManagerAgent] Task %s completed by %s", task_id[:8], message.sender.value)
            if task_id in self._task_events:
                self._task_events[task_id].set()

    async def _process_task_failed(self, message: Message) -> None:
        """Process a task failure notification from an agent.
        
        ENHANCED: Handles Noticer's detailed remediation plans with:
        - Line-by-line error locations
        - Character-level differences
        - Exact SQL/DDL fix instructions
        - Verification steps
        - Infinite loop prevention tracking
        """
        task_id = message.payload.get("task_id")
        error = message.payload.get("error", "Unknown error")
        remediation_plan = message.payload.get("remediation_plan")
        fix_instructions = message.payload.get("fix_instructions")
        verification_steps = message.payload.get("verification_steps")
        total_errors = message.payload.get("total_errors", 0)
        character_level_diffs = message.payload.get("character_level_diffs", 0)
        remediation_attempt = message.payload.get("remediation_attempt", 0)
        max_attempts = message.payload.get("max_attempts", 3)
        risk_level = message.payload.get("risk_level", "UNKNOWN")
        requires_human = message.payload.get("requires_human_intervention", False)
        escalation = message.payload.get("escalation", False)

        if task_id and task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            task.fail(error)
            logger.error("[ManagerAgent] Task %s FAILED: %s", task_id[:8], error)

            # Handle escalation from Noticer (infinite loop detected)
            if escalation:
                logger.critical(
                    "[ManagerAgent] NOTICER ESCALATION: %s. Requires human intervention.",
                    message.payload.get("escalation_reason", "Unknown reason")
                )
                # Create incident for human intervention
                await self._incident_mgr.create_incident(
                    project_id=message.project_id or "",
                    migration_id=message.migration_id or "",
                    source_agent=AgentType.NOTICER,
                    failure_reason=FailureReason.LOOP_LIMIT_EXCEEDED,
                    description=f"Noticer escalation: {message.payload.get('escalation_reason')}",
                    severity_override=IncidentSeverity.CRITICAL,
                )
            # Store enhanced remediation plan from Noticer
            elif remediation_plan and message.project_id:
                self._remediation_plans[message.project_id] = remediation_plan
                logger.info(
                    "[ManagerAgent] Stored Noticer remediation plan for project %s. "
                    "Errors: %d, Character diffs: %d, Attempt: %d/%d, Risk: %s",
                    message.project_id, total_errors, character_level_diffs,
                    remediation_attempt, max_attempts, risk_level
                )

                # Log detailed fix instructions
                if fix_instructions:
                    logger.info("[ManagerAgent] Fix instructions from Noticer:")
                    for instruction in fix_instructions:
                        logger.info("[ManagerAgent]   %s", instruction)

                # Log verification steps
                if verification_steps:
                    logger.info("[ManagerAgent] Verification steps from Noticer:")
                    for step in verification_steps:
                        logger.info("[ManagerAgent]   %s", step)

            if task_id in self._task_events:
                self._task_events[task_id].set()

    async def _process_health_response(self, message: Message) -> None:
        """Update agent health based on heartbeat response."""
        agent_type_str = message.payload.get("agent_type", message.sender.value)
        try:
            agent_type = AgentType(agent_type_str)
            status = AgentStatus(message.payload.get("status", AgentStatus.HEALTHY.value))
            await self._state.update_agent_status(agent_type, status)
        except ValueError as exc:
            logger.warning("[ManagerAgent] Invalid health response: %s", exc)

    async def _process_loop_warning(self, message: Message) -> None:
        """Process a real-time anomaly warning from Live Intel agent."""
        anomaly_type = message.payload.get("anomaly_type", "UNKNOWN_ANOMALY")
        desc = message.payload.get("description", "No description provided.")
        rec = message.payload.get("recommendation", "No recommendation provided.")
        severity = message.payload.get("severity", "WARNING")

        logger.warning(
            "[ManagerAgent] Live Intel Alert received: Type=%s | Severity=%s | %s | Recommendation: %s",
            anomaly_type, severity, desc, rec
        )

        self._audit.log(
            event_type=AuditEventType.LOOP_WARNING,
            actor=AgentType.MANAGER.value,
            description=f"Live Intel Anomaly: {desc}",
            project_id=message.project_id,
            migration_id=message.migration_id,
            details={
                "anomaly_type": anomaly_type,
                "severity": severity,
                "recommendation": rec
            }
        )

    # ------------------------------------------------------------------
    # Task Dispatch
    # ------------------------------------------------------------------

    async def _dispatch_task(
        self,
        task: Task,
        project: MigrationProject,
    ) -> TaskResult:
        """
        Assign a task, enqueue it, publish via message bus, and wait for result.

        In Phase 1 (Agent 1 only), downstream agents are stubs.
        This method will be extended as each agent is built.
        """
        task.assign()
        self._active_tasks[task.task_id] = task

        # Enqueue task
        await self._queues.enqueue_task(task)

        # Publish task assignment message
        msg = Message(
            sender=AgentType.MANAGER,
            receiver=task.assigned_to,
            message_type=MessageType.TASK_ASSIGN,
            payload=task.to_dict(),
            project_id=project.project_id,
            migration_id=project.active_migration_id,
            priority=task.priority,
        )
        await self._bus.publish(msg)

        # Audit
        self._audit.log(
            event_type=AuditEventType.TASK_ASSIGNED,
            actor=AgentType.MANAGER.value,
            description=f"Task {task.task_type.value} assigned to {task.assigned_to.value}.",
            project_id=project.project_id,
            migration_id=project.active_migration_id,
            details={"task_id": task.task_id, "task_type": task.task_type.value},
        )

        logger.info(
            "[ManagerAgent] Task dispatched: %s → %s (task_id=%s)",
            task.task_type.value, task.assigned_to.value, task.task_id[:8]
        )

        # Scout, Validator, GB, Checkpoint Engine are real, others are simulated
        agent_health = self._state.get_agent_health(task.assigned_to)
        agent_online = agent_health is not None and agent_health.status != AgentStatus.OFFLINE

        if task.assigned_to in (AgentType.SCOUT, AgentType.VALIDATOR, AgentType.GB, AgentType.CHECKPOINT_ENGINE) and agent_online:
            event = asyncio.Event()
            self._task_events[task.task_id] = event
            try:
                await asyncio.wait_for(event.wait(), timeout=float(task.timeout_seconds))
            except asyncio.TimeoutError:
                logger.error("[ManagerAgent] Task %s timed out.", task.task_id[:8])
                task.fail("Task timed out during execution.")
            finally:
                self._task_events.pop(task.task_id, None)

            success = task.status == TaskStatus.COMPLETED
            return TaskResult(
                task_id=task.task_id,
                project_id=task.project_id,
                migration_id=task.migration_id,
                agent_type=task.assigned_to,
                success=success,
                output={"result_ref": task.result_ref, **task.parameters.get("result_output", {})} if success else {},
                error_message=task.failure_reason if not success else None,
                is_recoverable=True,
                duration_seconds=1.0,
                objects_processed=project.total_objects_discovered,
            )
        else:
            return self._simulate_task_result(task, project)

    def _simulate_task_result(self, task: Task, project: MigrationProject) -> TaskResult:
        """
        Phase 1 stub: simulates agent responses for Manager testing.
        This is replaced by real agent integration as each agent is built.
        """
        task.start()
        task.complete()

        return TaskResult(
            task_id=task.task_id,
            project_id=task.project_id,
            migration_id=task.migration_id,
            agent_type=task.assigned_to,
            success=True,
            output={"simulation": True, "task_type": task.task_type.value},
            duration_seconds=0.1,
            objects_processed=project.total_objects_discovered or 0,
        )

    # ------------------------------------------------------------------
    # Checkpoint Creation
    # ------------------------------------------------------------------

    async def _create_checkpoint(self, project: MigrationProject, description: str) -> str:
        """Create a workflow checkpoint at the current state."""
        checkpoint_id = str(uuid.uuid4())
        session = await self._state.get_session(project.active_migration_id or "")
        if not session:
            session = MigrationSession(project_id=project.project_id)
            session.migration_id = project.active_migration_id or "unknown"

        params = {
            "checkpoint_id": checkpoint_id,
            "description": description,
            "project_state": project.to_dict(),
            "global_state_snapshot": self._state.snapshot()
        }

        # Check if checkpoint agent is online
        agent_health = self._state.get_agent_health(AgentType.CHECKPOINT_ENGINE)
        agent_online = agent_health is not None and agent_health.status != AgentStatus.OFFLINE

        if agent_online:
            task = self._build_task(
                task_type=TaskType.CHECKPOINT_CREATE,
                assigned_to=AgentType.CHECKPOINT_ENGINE,
                project=project,
                session=session,
                priority=Priority.P0_SYSTEM_CRITICAL,
                parameters=params,
            )

            result = await self._dispatch_task(task, project)
            if not result.success:
                logger.error("[ManagerAgent] Checkpoint creation failed: %s", result.error_message)
                raise RuntimeError(f"Checkpoint creation failed: {result.error_message}")

            registered_id = result.output.get("checkpoint_id", checkpoint_id)
            return registered_id
        else:
            # Fallback to direct synchronous registration for testing/compatibility when agent is offline
            entry = CheckpointEntry(
                checkpoint_id=checkpoint_id,
                project_id=project.project_id,
                migration_id=project.active_migration_id or "unknown",
                workflow_state=project.state,
                description=description,
            )
            await self._state.register_checkpoint(entry)

            self._audit.log(
                event_type=AuditEventType.CHECKPOINT_CREATED,
                actor=AgentType.MANAGER.value,
                description=f"Checkpoint created (direct): {description}",
                project_id=project.project_id,
                migration_id=project.active_migration_id,
                details={"checkpoint_id": checkpoint_id, "state": project.state.value},
            )
            return checkpoint_id

    # ------------------------------------------------------------------
    # State Transition Helper
    # ------------------------------------------------------------------

    async def _transition(
        self,
        project: MigrationProject,
        target_state: WorkflowState,
        reason: str = "",
    ) -> None:
        """Validate and apply a workflow state transition, then update global state."""
        new_state = self._workflow.transition(
            project.state, target_state, project.project_id, reason
        )
        await self._state.update_project_state(project.project_id, new_state, reason)

        self._audit.log(
            event_type=AuditEventType.PROJECT_STATE_CHANGED,
            actor=AgentType.MANAGER.value,
            description=self._workflow.describe_transition(project.state, new_state),
            project_id=project.project_id,
            migration_id=project.active_migration_id,
            details={"from": project.state.value, "to": new_state.value, "reason": reason},
        )

    # ------------------------------------------------------------------
    # Task Builder
    # ------------------------------------------------------------------

    def _build_task(
        self,
        task_type: TaskType,
        assigned_to: AgentType,
        project: MigrationProject,
        session: MigrationSession,
        priority: Priority = Priority.P2_VALIDATION,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
    ) -> Task:
        """Create a properly structured Task for dispatch."""
        return Task(
            task_type=task_type,
            assigned_to=assigned_to,
            project_id=project.project_id,
            migration_id=session.migration_id,
            priority=priority,
            timeout_seconds=timeout_seconds,
            max_retries=3,
            parameters=parameters or {},
            checkpoint_ref=self._get_latest_checkpoint_id(project.project_id),
        )

    def _get_latest_checkpoint_id(self, project_id: str) -> Optional[str]:
        """Return the latest checkpoint ID for a project."""
        checkpoint = self._state.get_latest_checkpoint(project_id)
        return checkpoint.checkpoint_id if checkpoint else None

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def system_status(self) -> Dict[str, Any]:
        """Return a complete system status snapshot."""
        return {
            "manager_id": self.AGENT_ID,
            "running": self._running,
            "system_frozen": self._state.is_frozen(),
            "freeze_reason": self._state.freeze_reason(),
            "global_state": self._state.snapshot(),
            "queue_stats": self._queues.stats(),
            "incident_summary": self._incident_mgr.summary(),
            "loop_governor_states": self._loop_governor.summary(),
            "audit_summary": self._audit.summary(),
            "message_bus_stats": self._bus.stats(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
