"""Core WorkflowEngine Orchestrator Facade."""

import threading
from typing import Any, Dict, List, Tuple
from akaal.workflow.checkpoint.manager import CheckpointManager
from akaal.workflow.events.dispatcher import IEventDispatcher, InMemoryEventDispatcher
from akaal.workflow.events.events import StepExecutedEvent, WorkflowStateChangedEvent
from akaal.workflow.exceptions import (
    LockAcquisitionException,
    ManifestValidationException,
    WorkflowException,
)
from akaal.workflow.execution.executor import StepExecutor
from akaal.workflow.execution.policies import FixedRetryPolicy, FixedTimeoutPolicy
from akaal.workflow.execution_records.records import WorkflowExecutionTrace, WorkflowMetrics
from akaal.workflow.interfaces.base import IEngine, IWorkflowLock
from akaal.workflow.locks.lock import InMemoryLock
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import WorkflowManifest
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.models.sub_contexts import ExecutionContext, RuntimeContext, UserContext
from akaal.workflow.registry.registry import WorkflowStepRegistry
from akaal.workflow.state_machine.controller import StateController
from akaal.workflow.state_machine.states import WorkflowState
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class WorkflowEngine(IEngine):
    """High-level Orchestration Coordinator.
    
    Coordinates StateController, StepExecutor, CheckpointManager, WorkflowStepRegistry,
    IEventDispatcher, and IWorkflowLock following SOLID principles.
    """

    def __init__(
        self,
        registry: WorkflowStepRegistry | None = None,
        executor: StepExecutor | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        event_dispatcher: IEventDispatcher | None = None,
        lock: IWorkflowLock | None = None,
        clock: IClock | None = None,
        id_generator: IIdGenerator | None = None,
    ) -> None:
        self._registry = registry or WorkflowStepRegistry()
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()
        self._executor = executor or StepExecutor(clock=self._clock)
        self._checkpoint_manager = checkpoint_manager or CheckpointManager(clock=self._clock, id_generator=self._id_generator)
        self._event_dispatcher = event_dispatcher or InMemoryEventDispatcher()
        self._lock = lock or InMemoryLock()

        self._manifests: Dict[str, WorkflowManifest] = {}
        self._state_controllers: Dict[str, StateController] = {}
        self._pause_requests: set[str] = set()
        self._cancel_requests: set[str] = set()
        self._mutex = threading.Lock()

    def register_manifest(self, manifest: WorkflowManifest) -> None:
        """Register a workflow manifest for execution."""
        with self._mutex:
            self._manifests[manifest.metadata.workflow_id] = manifest

    def execute(self, workflow_id: str, parameters: dict[str, Any] | None = None) -> WorkflowExecutionTrace:
        """Execute a registered workflow from the beginning."""
        manifest = self._get_manifest(workflow_id)
        run_id = self._id_generator.generate_uuid()

        if not self._lock.acquire_lock(workflow_id, ttl_seconds=300):
            raise LockAcquisitionException(workflow_id, "Workflow is currently locked by another process.")

        try:
            controller = StateController(initial_state=WorkflowState.CREATED, clock=self._clock)
            with self._mutex:
                self._state_controllers[workflow_id] = controller

            # Transition CREATED -> READY
            self._change_state(workflow_id, controller, WorkflowState.READY, "Manifest initialized and validated")

            # Initialize WorkflowContext
            exec_ctx = ExecutionContext(
                workflow_id=workflow_id,
                run_id=run_id,
                pending_steps=tuple([s.step_id for s in manifest.step_definitions]),
            )
            rt_ctx = RuntimeContext(transient_parameters=parameters or {})
            user_ctx = UserContext(
                user_id=manifest.metadata.requested_by,
                tenant_id=manifest.metadata.tenant_id,
                security_context=manifest.metadata.security_context,
                correlation_id=manifest.metadata.correlation_id,
                trace_parent=manifest.metadata.trace_parent,
            )
            context = WorkflowContext(
                execution_context=exec_ctx,
                runtime_context=rt_ctx,
                user_context=user_ctx,
            )

            # Transition READY -> RUNNING
            self._change_state(workflow_id, controller, WorkflowState.RUNNING, "Starting step execution pipeline")

            return self._run_execution_loop(manifest, context, controller)
        finally:
            self._lock.release_lock(workflow_id)

    def pause(self, workflow_id: str) -> None:
        """Request a runtime pause at the next step boundary."""
        with self._mutex:
            self._pause_requests.add(workflow_id)

    def resume(self, workflow_id: str) -> WorkflowExecutionTrace:
        """Resume execution of a PAUSED or WAITING_FOR_APPROVAL workflow from latest checkpoint."""
        manifest = self._get_manifest(workflow_id)
        controller = self._state_controllers.get(workflow_id)
        if not controller:
            raise WorkflowException(f"No state controller found for workflow {workflow_id}")

        if not self._lock.acquire_lock(workflow_id, ttl_seconds=300):
            raise LockAcquisitionException(workflow_id, "Workflow is currently locked.")

        try:
            # Transition PAUSED/WAITING_FOR_APPROVAL -> RUNNING
            self._change_state(workflow_id, controller, WorkflowState.RUNNING, "Resuming execution via resume action")
            
            latest_cp = self._checkpoint_manager.get_latest_checkpoint(
                workflow_id, controller.current_state.value
            )
            if not latest_cp:
                # Find latest checkpoint across any run
                cps = self._checkpoint_manager.list_checkpoints(workflow_id)
                if not cps:
                    raise WorkflowException(f"No checkpoint found to resume workflow {workflow_id}")
                latest_cp = cps[-1]

            context = latest_cp.context
            with self._mutex:
                self._pause_requests.discard(workflow_id)

            return self._run_execution_loop(manifest, context, controller, from_step_index=len(latest_cp.completed_steps))
        finally:
            self._lock.release_lock(workflow_id)

    def restart(self, workflow_id: str, force_from_start: bool = False) -> WorkflowExecutionTrace:
        """Restart workflow execution, by default attempting recovery from checkpoint unless force_from_start=True."""
        if force_from_start:
            return self.execute(workflow_id)
        return self.resume(workflow_id)

    def cancel(self, workflow_id: str) -> None:
        """Cancel a running or paused workflow."""
        with self._mutex:
            self._cancel_requests.add(workflow_id)
            controller = self._state_controllers.get(workflow_id)
            if controller and not controller.is_terminal():
                self._change_state(workflow_id, controller, WorkflowState.CANCELLED, "Explicit user cancellation")

    def rollback(self, workflow_id: str) -> WorkflowExecutionTrace:
        """Trigger compensating rollback for completed steps in a workflow."""
        manifest = self._get_manifest(workflow_id)
        controller = self._state_controllers.get(workflow_id)
        if not controller:
            raise WorkflowException(f"No state controller for workflow {workflow_id}")

        if not self._lock.acquire_lock(workflow_id, ttl_seconds=300):
            raise LockAcquisitionException(workflow_id, "Workflow locked")

        try:
            self._change_state(workflow_id, controller, WorkflowState.ROLLING_BACK, "Initiating compensating rollback")
            cps = self._checkpoint_manager.list_checkpoints(workflow_id)
            context = cps[-1].context if cps else WorkflowContext(
                execution_context=ExecutionContext(workflow_id=workflow_id, run_id=self._id_generator.generate_uuid())
            )

            # Rollback steps in reverse order
            results: list[WorkflowStepResult] = []
            for step_def in reversed(manifest.step_definitions):
                step = self._registry.resolve(step_def.step_type, step_def.step_id)
                rb_res = step.rollback(context)
                results.append(rb_res)

            self._change_state(workflow_id, controller, WorkflowState.ROLLED_BACK, "Compensating rollback complete")
            return WorkflowExecutionTrace(
                run_id=context.run_id,
                workflow_id=workflow_id,
                step_results=tuple(results),
                state_transitions=controller.transition_records,
                start_time=self._clock.now_utc(),
                end_time=self._clock.now_utc(),
            )
        finally:
            self._lock.release_lock(workflow_id)

    def _run_execution_loop(
        self,
        manifest: WorkflowManifest,
        initial_context: WorkflowContext,
        controller: StateController,
        from_step_index: int = 0,
    ) -> WorkflowExecutionTrace:
        """Core step loop delegating step invocation to StepExecutor and resolving steps via WorkflowStepRegistry."""
        context = initial_context
        step_results: list[WorkflowStepResult] = []
        completed_steps: list[str] = list(context.execution_context.completed_steps)
        start_time = self._clock.now_utc()

        step_defs = manifest.step_definitions[from_step_index:]

        for step_def in step_defs:
            # Check pause or cancel requests
            if manifest.metadata.workflow_id in self._pause_requests:
                self._change_state(manifest.metadata.workflow_id, controller, WorkflowState.PAUSING, "Pause requested")
                self._change_state(manifest.metadata.workflow_id, controller, WorkflowState.PAUSED, "Paused at step boundary")
                # Save checkpoint at pause boundary
                self._checkpoint_manager.create_checkpoint(
                    context=context,
                    step_id=step_def.step_id,
                    state=WorkflowState.PAUSED.value,
                    completed_steps=tuple(completed_steps),
                    pending_steps=tuple([s.step_id for s in step_defs if s.step_id not in completed_steps]),
                )
                break

            if manifest.metadata.workflow_id in self._cancel_requests or controller.current_state == WorkflowState.CANCELLED:
                if controller.current_state != WorkflowState.CANCELLED:
                    self._change_state(manifest.metadata.workflow_id, controller, WorkflowState.CANCELLED, "Cancelled at step boundary")
                break

            # Resolve step using registry ONLY
            step_instance = self._registry.resolve(step_def.step_type, step_def.step_id)

            # Delegate step execution to StepExecutor -> ExecutionPipeline
            retry_pol = FixedRetryPolicy(delay_seconds=0.1) if step_def.max_retries > 0 else None
            timeout_pol = FixedTimeoutPolicy() if step_def.timeout_seconds > 0 else None

            res, context = self._executor.execute_step(
                step=step_instance,
                context=context,
                timeout_seconds=step_def.timeout_seconds,
                max_retries=step_def.max_retries,
                retry_policy=retry_pol,
                timeout_policy=timeout_pol,
            )
            step_results.append(res)

            # Emit StepExecutedEvent via IEventDispatcher
            self._event_dispatcher.dispatch(
                StepExecutedEvent(
                    event_id=self._id_generator.generate_uuid(),
                    event_type="StepExecuted",
                    workflow_id=manifest.metadata.workflow_id,
                    timestamp=self._clock.now_utc(),
                    payload=res.to_dict(),
                )
            )

            if not res.success:
                # Transition RUNNING -> ROLLING_BACK -> FAILED
                self._change_state(manifest.metadata.workflow_id, controller, WorkflowState.FAILED, f"Step {step_def.step_id} failed")
                break

            completed_steps.append(step_def.step_id)
            context = context.with_updates(
                execution_updates={
                    "completed_steps": tuple(completed_steps),
                    "pending_steps": tuple([s.step_id for s in manifest.step_definitions if s.step_id not in completed_steps]),
                }
            )

            # Create checkpoint if step requested it or reached key milestone
            if res.checkpoint_created:
                self._checkpoint_manager.create_checkpoint(
                    context=context,
                    step_id=step_def.step_id,
                    state=controller.current_state.value,
                    completed_steps=tuple(completed_steps),
                    pending_steps=tuple([s.step_id for s in manifest.step_definitions if s.step_id not in completed_steps]),
                )

        if controller.current_state == WorkflowState.RUNNING:
            self._change_state(manifest.metadata.workflow_id, controller, WorkflowState.COMPLETED, "All steps executed successfully")

        return WorkflowExecutionTrace(
            run_id=context.run_id,
            workflow_id=manifest.metadata.workflow_id,
            step_results=tuple(step_results),
            state_transitions=controller.transition_records,
            start_time=start_time,
            end_time=self._clock.now_utc(),
        )

    def _change_state(self, workflow_id: str, controller: StateController, target: WorkflowState, reason: str) -> None:
        rec = controller.transition_to(target, reason)
        self._event_dispatcher.dispatch(
            WorkflowStateChangedEvent(
                event_id=self._id_generator.generate_uuid(),
                event_type="WorkflowStateChanged",
                workflow_id=workflow_id,
                timestamp=self._clock.now_utc(),
                payload=rec.to_dict(),
            )
        )

    def _get_manifest(self, workflow_id: str) -> WorkflowManifest:
        with self._mutex:
            manifest = self._manifests.get(workflow_id)
            if not manifest:
                raise WorkflowException(f"Workflow manifest for ID '{workflow_id}' not registered.")
            return manifest
