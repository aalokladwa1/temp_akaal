"""
Enterprise Generic Workflow Engine facade.
The WorkflowEngine orchestrates workflow execution strictly by delegating to specialized controllers:
- StateController
- StepExecutor
- CheckpointCoordinator
- SessionCoordinator
- ApprovalCoordinator
- AuditCoordinator
- RecoveryCoordinator

The WorkflowEngine orchestrates execution only. It contains ZERO database, schema conversion, or CDC logic.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
import time

from akaal.orchestration.domain.identifiers import JobId, WorkflowId, SessionId, ConfigurationId
from akaal.orchestration.domain.types import EngineState, WorkflowStepName, Version, AuditMetadata
from akaal.orchestration.domain.errors import (
    WorkflowError,
    WorkflowExecutionError,
    InvalidStateTransitionError,
)
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.session.session import WorkflowSession, SessionStatus
from akaal.orchestration.config.config import FrozenConfiguration, UnifiedConfigurationManager
from akaal.orchestration.repository.interfaces import (
    WorkflowRepository,
    SessionRepository,
    CheckpointRepository,
    AuditRepository,
)
from akaal.orchestration.repository.memory_repository import (
    InMemoryWorkflowRepository,
    InMemorySessionRepository,
    InMemoryCheckpointRepository,
    InMemoryAuditRepository,
)
from akaal.orchestration.events.events import (
    InProcessEventDispatcher,
    WorkflowStarted,
    WorkflowCompleted,
    WorkflowFailed,
    StateTransitioned,
)
from akaal.orchestration.workflow.definition import WorkflowDefinition
from akaal.orchestration.workflow.context import WorkflowContext, CancellationToken
from akaal.orchestration.engine.state_controller import StateController
from akaal.orchestration.engine.step_executor import StepExecutor
from akaal.orchestration.engine.checkpoint_coordinator import CheckpointCoordinator
from akaal.orchestration.engine.session_coordinator import SessionCoordinator
from akaal.orchestration.engine.approval_coordinator import ApprovalCoordinator
from akaal.orchestration.engine.audit_coordinator import AuditCoordinator
from akaal.orchestration.engine.recovery_coordinator import RecoveryCoordinator
from akaal.orchestration.engine.metrics import MetricsCollector, InMemoryMetricsCollector

logger = logging.getLogger("nexusforge.orchestration.engine")


class WorkflowEngine:
    """
    Enterprise Generic Workflow Engine.
    Orchestrates execution of WorkflowDefinition blueprints using specialized coordinators.
    """

    def __init__(
        self,
        workflow_repo: Optional[WorkflowRepository] = None,
        session_repo: Optional[SessionRepository] = None,
        checkpoint_repo: Optional[CheckpointRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        dispatcher: Optional[InProcessEventDispatcher] = None,
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        self.workflow_repo = workflow_repo or InMemoryWorkflowRepository()
        self.session_repo = session_repo or InMemorySessionRepository()
        self.checkpoint_repo = checkpoint_repo or InMemoryCheckpointRepository()
        self.audit_repo = audit_repo or InMemoryAuditRepository()
        self.dispatcher = dispatcher or InProcessEventDispatcher()
        self.metrics = metrics or InMemoryMetricsCollector()

        # Controllers & Coordinators
        self.state_controller = StateController()
        self.step_executor = StepExecutor()
        self.checkpoint_coordinator = CheckpointCoordinator(self.checkpoint_repo, self.dispatcher)
        self.session_coordinator = SessionCoordinator(self.session_repo, self.dispatcher)
        self.approval_coordinator = ApprovalCoordinator(self.workflow_repo, self.dispatcher)
        self.audit_coordinator = AuditCoordinator(self.dispatcher, self.audit_repo)
        self.recovery_coordinator = RecoveryCoordinator(self.checkpoint_repo, self.session_repo, self.dispatcher)

    def _update_job_state(
        self,
        job: MigrationJob,
        target_state: EngineState,
        target_step: Optional[str] = None,
        updated_by: str = "engine",
    ) -> MigrationJob:
        """Validates state transition and updates MigrationJob in repository."""
        self.state_controller.validate_transition(job.current_state, target_state)
        
        from_st = job.current_state.value
        updated_job = job.with_updates(
            current_state=target_state,
            current_step=target_step,
            updated_by=updated_by,
        )
        self.workflow_repo.update_job(updated_job)
        
        self.metrics.record_transition(from_st, target_state.value)
        w_id = str(job.workflow_id)
        self.dispatcher.publish(
            StateTransitioned(
                aggregate_id=w_id,
                workflow_id=w_id,
                job_id=str(job.job_id),
                from_state=from_st,
                to_state=target_state.value,
            )
        )
        return updated_job

    def create_job(
        self,
        source_profile: Dict[str, Any],
        target_profile: Dict[str, Any],
        workflow_id: Optional[WorkflowId] = None,
        config: Optional[FrozenConfiguration] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[MigrationJob, WorkflowSession]:
        """Creates a new MigrationJob and associated WorkflowSession."""
        j_id = JobId.generate()
        w_id = workflow_id or WorkflowId.generate()
        cfg = config or UnifiedConfigurationManager().build_config()

        session = self.session_coordinator.create_session(workflow_id=w_id, job_id=j_id)

        job = MigrationJob(
            job_id=j_id,
            workflow_id=w_id,
            session_id=session.session_id,
            config_id=cfg.config_id,
            source_profile=source_profile,
            target_profile=target_profile,
            metadata=metadata or {},
            current_state=EngineState.CREATED,
            current_step=WorkflowStepName.ANALYSIS.value,
        )
        self.workflow_repo.save_job(job)
        return job, session

    def execute_workflow(
        self,
        job: MigrationJob,
        definition: WorkflowDefinition,
        config: FrozenConfiguration,
        session: WorkflowSession,
        start_step_name: Optional[str] = None,
    ) -> MigrationJob:
        """
        Executes a WorkflowDefinition from start_step_name (or first step) to completion.
        Maintains deterministic execution, checkpointing, session heartbeats, and audit events.
        """
        # Transition CREATED -> READY -> RUNNING
        if job.current_state == EngineState.CREATED:
            job = self._update_job_state(job, EngineState.READY)

        job = self._update_job_state(job, EngineState.RUNNING)

        w_id = str(job.workflow_id)
        self.dispatcher.publish(
            WorkflowStarted(
                aggregate_id=w_id,
                workflow_id=w_id,
                job_id=str(job.job_id),
                initial_step=definition.steps[0].name if definition.steps else "",
            )
        )

        context = WorkflowContext(
            job=job,
            session=session,
            config=config,
            workflow_repo=self.workflow_repo,
            session_repo=self.session_repo,
            checkpoint_repo=self.checkpoint_repo,
            audit_repo=self.audit_repo,
            publisher=self.dispatcher,
            metrics=self.metrics,
        )

        steps = definition.steps
        start_idx = 0
        if start_step_name:
            for idx, s in enumerate(steps):
                if s.name == start_step_name:
                    start_idx = idx
                    break

        start_time = time.time()

        for idx in range(start_idx, len(steps)):
            step = steps[idx]
            
            # Heartbeat check
            self.session_coordinator.heartbeat(session.session_id)

            # Check if paused
            if job.current_state == EngineState.PAUSED:
                logger.info(f"Workflow '{w_id}' paused before step '{step.name}'.")
                return job

            # Execute step
            step_start = time.time()
            try:
                job = job.with_updates(current_step=step.name)
                self.workflow_repo.update_job(job)
                context = context.with_job(job)

                step_output = self.step_executor.execute_step(step, context, step_index=idx)
                step_duration = time.time() - step_start
                self.metrics.record_step(step.name, "SUCCESS", step_duration)

                # Capture checkpoint
                cp_data = step.checkpoint(context)
                self.checkpoint_coordinator.create_checkpoint(
                    workflow_id=job.workflow_id,
                    job_id=job.job_id,
                    step_name=step.name,
                    step_index=idx,
                    engine_state=job.current_state,
                    workflow_version=definition.version,
                    config_version=int(config.version),
                    config_checksum=str(config.checksum),
                    state_data=cp_data,
                )

                # Check if approval required for next step
                approval_rule = definition.approval_rules.get(step.name)
                if approval_rule and approval_rule.get("require_approval", False):
                    app_id = self.approval_coordinator.request_approval(
                        workflow_id=job.workflow_id,
                        step_name=step.name,
                        required_roles=approval_rule.get("roles", ["ADMIN"]),
                    )
                    job = self._update_job_state(job, EngineState.WAITING_FOR_APPROVAL, target_step=step.name)
                    return job

            except Exception as exc:
                step_duration = time.time() - step_start
                self.metrics.record_step(step.name, "FAILED", step_duration)
                logger.error(f"Workflow '{w_id}' failed during step '{step.name}': {str(exc)}")
                job = self._update_job_state(job, EngineState.FAILED, target_step=step.name)
                self.dispatcher.publish(
                    WorkflowFailed(
                        aggregate_id=w_id,
                        workflow_id=w_id,
                        job_id=str(job.job_id),
                        failed_step=step.name,
                        error_message=str(exc),
                    )
                )
                raise WorkflowExecutionError(f"Workflow execution failed at step '{step.name}': {str(exc)}") from exc

        # Mark COMPLETED
        duration = time.time() - start_time
        job = self._update_job_state(job, EngineState.COMPLETED, target_step=steps[-1].name if steps else "")
        self.session_coordinator.close_session(session.session_id)
        self.audit_coordinator.flush_audit_records()

        self.dispatcher.publish(
            WorkflowCompleted(
                aggregate_id=w_id,
                workflow_id=w_id,
                job_id=str(job.job_id),
                final_step=steps[-1].name if steps else "",
                duration_seconds=duration,
            )
        )

        return job

    def pause_workflow(self, job: MigrationJob) -> MigrationJob:
        """Pause a running workflow."""
        return self._update_job_state(job, EngineState.PAUSED)

    def resume_workflow(
        self,
        job: MigrationJob,
        definition: WorkflowDefinition,
        config: FrozenConfiguration,
        session: WorkflowSession,
    ) -> MigrationJob:
        """
        Deterministically recovers session/checkpoint state and resumes execution.
        """
        rec_start = time.time()
        # Validate deterministic recovery
        checkpoint, state_data = self.recovery_coordinator.validate_and_recover(
            workflow_id=job.workflow_id,
            definition=definition,
            config=config,
            session=session,
        )
        rec_duration = time.time() - rec_start
        self.metrics.record_duration("recovery", rec_duration)

        # Transition PAUSED/ROLLED_BACK -> READY
        if job.current_state in (EngineState.PAUSED, EngineState.ROLLED_BACK):
            job = self._update_job_state(job, EngineState.READY)

        # Find step to resume
        next_step_index = checkpoint.step_index + 1
        step_names = definition.get_step_names()

        if next_step_index >= len(step_names):
            # Already finished all steps: transition READY -> RUNNING -> COMPLETED
            job = self._update_job_state(job, EngineState.RUNNING)
            return self._update_job_state(job, EngineState.COMPLETED, target_step=checkpoint.step_name)

        next_step_name = step_names[next_step_index]
        return self.execute_workflow(
            job=job,
            definition=definition,
            config=config,
            session=session,
            start_step_name=next_step_name,
        )

    def rollback_workflow(
        self,
        job: MigrationJob,
        definition: WorkflowDefinition,
        config: FrozenConfiguration,
        session: WorkflowSession,
    ) -> MigrationJob:
        """
        Rollback executed workflow steps on failure.
        """
        if job.current_state not in (EngineState.FAILED, EngineState.RUNNING, EngineState.PAUSED):
            raise InvalidStateTransitionError(
                from_state=job.current_state.value,
                to_state=EngineState.ROLLED_BACK.value,
                reason="Rollback can only be initiated from FAILED, RUNNING, or PAUSED state."
            )

        rb_start = time.time()
        context = WorkflowContext(
            job=job,
            session=session,
            config=config,
            workflow_repo=self.workflow_repo,
            session_repo=self.session_repo,
            checkpoint_repo=self.checkpoint_repo,
            audit_repo=self.audit_repo,
            publisher=self.dispatcher,
            metrics=self.metrics,
        )

        # Rollback steps in reverse order
        for step in reversed(definition.steps):
            try:
                self.step_executor.rollback_step(step, context)
            except Exception as e:
                logger.error(f"Error during rollback of step '{step.name}': {str(e)}")

        rb_duration = time.time() - rb_start
        self.metrics.record_duration("rollback", rb_duration)

        job = self._update_job_state(job, EngineState.ROLLED_BACK)
        return job

    def cancel_workflow(self, job: MigrationJob) -> MigrationJob:
        """Cancel a workflow."""
        return self._update_job_state(job, EngineState.CANCELLED)
