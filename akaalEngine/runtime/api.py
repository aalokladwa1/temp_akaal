"""
akaalEngine.runtime.api
=======================
Single Canonical Entrypoint and Façade for Authority #6 — Runtime (`RuntimeAuthority`).
"""

from datetime import datetime, timezone
import logging
from threading import RLock
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from akaalEngine.runtime.distributed.coordinator import DistributedCoordinator
from akaalEngine.runtime.execution.local import BoundedThreadExecutor
from akaalEngine.runtime.execution.process import IsolatedProcessExecutor
from akaalEngine.runtime.journal.command_mailbox import DurableCommandMailbox
from akaalEngine.runtime.leases.manager import ExecutionLease, ExecutionLeaseManager
from akaalEngine.runtime.models import (
    FencingRejectedError,
    InvalidTaskTransitionError,
    LeaseExpiredError,
    PauseUnsupportedError,
    ResourceAdmissionError,
    ResourceAdmissionPolicy,
    ResourceBudget,
    ResourceRequirement,
    RuntimeEngineException,
    RuntimeNotStartedError,
    RuntimeShuttingDownError,
    TaskNotFoundError,
    TaskRejectedError,
    TaskSnapshot,
    TaskSpec,
    TaskState,
    WorkerNotFoundError,
    WorkerSnapshot,
    WorkerSpec,
    WorkerState,
    validate_task_transition,
)
from akaalEngine.runtime.recovery.coordinator import RuntimeRecoveryCoordinator, RuntimeRecoveryPlan
from akaalEngine.runtime.resources.adaptive import AdaptiveConcurrencyController
from akaalEngine.runtime.resources.admission import ResourceAdmissionController
from akaalEngine.runtime.workers.assignment import TaskAssignmentEngine
from akaalEngine.runtime.workers.heartbeat import WorkerHeartbeatTracker
from akaalEngine.runtime.workers.registry import WorkerRegistry

logger = logging.getLogger("akaalEngine.runtime.api")


class RuntimeAuthority:
    """
    Single Canonical Façade for Authority #6 — Runtime.
    Owns execution lifecycle, bounded local/process execution, worker state,
    resource admission, adaptive concurrency, execution leases, fencing,
    and restart recovery coordination.
    """

    def __init__(
        self,
        durability_authority: Optional[Any] = None,
        budget: Optional[ResourceBudget] = None,
        admission_policy: Optional[ResourceAdmissionPolicy] = None,
        max_threads: int = 16,
        max_processes: int = 4,
        heartbeat_timeout_seconds: float = 15.0,
    ) -> None:
        self.durability_authority = durability_authority
        self._is_running = False
        self._is_shutting_down = False
        self._lock = RLock()

        # Component initialization
        self.registry = WorkerRegistry()
        self.heartbeat_tracker = WorkerHeartbeatTracker(self.registry, heartbeat_timeout_seconds)
        self.assignment_engine = TaskAssignmentEngine(self.registry)
        self.admission_controller = ResourceAdmissionController(budget, admission_policy)
        self.adaptive_controller = AdaptiveConcurrencyController(min_workers=2, max_workers=max_threads)

        fencing_mgr = getattr(durability_authority, "fencing_manager", None) if durability_authority else None
        self.lease_manager = ExecutionLeaseManager(durability_fencing_manager=fencing_mgr)
        self.distributed_coordinator = DistributedCoordinator()
        self.recovery_coordinator = RuntimeRecoveryCoordinator(durability_authority)

        self.thread_executor = BoundedThreadExecutor(max_workers=max_threads)
        self.process_executor = IsolatedProcessExecutor(max_processes=max_processes)

        # Internal state maps
        self._specs: Dict[str, TaskSpec] = {}
        self._snapshots: Dict[str, TaskSnapshot] = {}

    def start(self) -> None:
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._is_shutting_down = False
            logger.info("[RuntimeAuthority] Runtime Authority started successfully.")

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if not self._is_running or self._is_shutting_down:
                return
            self._is_shutting_down = True
            logger.info("[RuntimeAuthority] Shutting down Runtime Authority...")

            # 1. Cancel running tasks
            for task_id, snap in list(self._snapshots.items()):
                if not snap.is_terminal:
                    self.cancel_task(task_id, reason="Runtime shutting down")

        # 2. Shutdown executors outside self._lock so completion callbacks in worker threads can acquire lock cleanly
        self.thread_executor.shutdown(wait=wait)
        self.process_executor.shutdown(wait=wait)

        with self._lock:
            self._is_running = False
            self._is_shutting_down = False
            logger.info("[RuntimeAuthority] Runtime Authority shutdown complete.")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running and not self._is_shutting_down

    def _ensure_running(self) -> None:
        if not self._is_running:
            raise RuntimeNotStartedError()
        if self._is_shutting_down:
            raise RuntimeShuttingDownError()

    def get_task_status(self, task_id: str) -> TaskState:
        """Returns the current state of a task, or UNSPECIFIED if not found."""
        with self._lock:
            snap = self._snapshots.get(task_id)
            if snap:
                return snap.state
            return TaskState.UNSPECIFIED

    def restore_task(self, spec: TaskSpec) -> TaskSnapshot:
        """Restores a task from a recovery snapshot / specification."""
        with self._lock:
            self._ensure_running()
            return self.submit_task(spec)

    # --- Task Submission & Lifecycle ---
    def submit_task(self, spec: TaskSpec) -> TaskSnapshot:
        with self._lock:
            self._ensure_running()

            if spec.task_id in self._snapshots and not self._snapshots[spec.task_id].is_terminal:
                raise TaskRejectedError(f"Task '{spec.task_id}' already exists in non-terminal state.")

            # Resource Admission
            req = ResourceRequirement(
                cpu_cores=spec.cpu_cores_required,
                memory_mb=spec.memory_mb_required,
                concurrency_slots=1,
                weight=spec.weight,
            )

            can_admit, reason = self.admission_controller.evaluate_admission(req)
            if not can_admit:
                raise ResourceAdmissionError(reason or "Admission denied")

            self.admission_controller.allocate(req)
            self._specs[spec.task_id] = spec

            now_str = datetime.now(timezone.utc).isoformat()
            snap = TaskSnapshot(
                task_id=spec.task_id,
                task_type=spec.task_type,
                state=TaskState.ADMITTED,
                submitted_at=now_str,
            )
            self._snapshots[spec.task_id] = snap

            # Attempt worker assignment and execution dispatch
            try:
                worker = self.assignment_engine.select_worker(spec)
                lease = self.lease_manager.acquire_lease(spec.task_id, worker.worker_id)
                self.registry.assign_task(worker.worker_id, spec.task_id)

                snap_assigned = TaskSnapshot(
                    task_id=spec.task_id,
                    task_type=spec.task_type,
                    state=TaskState.ASSIGNED,
                    worker_id=worker.worker_id,
                    lease_id=lease.lease_id,
                    attempt_id=lease.attempt_id,
                    fencing_epoch=lease.fencing_epoch,
                    submitted_at=now_str,
                )
                self._snapshots[spec.task_id] = snap_assigned
                self._dispatch_execution(spec, snap_assigned)
                return self._snapshots[spec.task_id]
            except Exception as exc:
                logger.info(f"[RuntimeAuthority] Task '{spec.task_id}' admitted to pending queue: {exc}")
                snap_admitted = TaskSnapshot(
                    task_id=spec.task_id,
                    task_type=spec.task_type,
                    state=TaskState.PENDING,
                    submitted_at=now_str,
                )
                self._snapshots[spec.task_id] = snap_admitted
                return snap_admitted

    def _dispatch_execution(self, spec: TaskSpec, snap: TaskSnapshot) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        snap_running = TaskSnapshot(
            task_id=spec.task_id,
            task_type=spec.task_type,
            state=TaskState.RUNNING,
            worker_id=snap.worker_id,
            lease_id=snap.lease_id,
            attempt_id=snap.attempt_id,
            fencing_epoch=snap.fencing_epoch,
            submitted_at=snap.submitted_at,
            started_at=now_str,
        )
        self._snapshots[spec.task_id] = snap_running

        def _completion_cb(t_id: str, result: Optional[Any], exc: Optional[Exception]) -> None:
            with self._lock:
                req = ResourceRequirement(spec.cpu_cores_required, spec.memory_mb_required, 1, spec.weight)
                self.admission_controller.release(req)
                if snap.worker_id:
                    self.registry.unassign_task(snap.worker_id, t_id)
                if snap.lease_id:
                    self.lease_manager.release_lease(snap.lease_id)

                fin_str = datetime.now(timezone.utc).isoformat()
                current_snap = self._snapshots.get(t_id)

                # Do not overwrite terminal task states (e.g. CANCELLED or FAILED)
                if current_snap and current_snap.is_terminal:
                    return

                if current_snap and current_snap.state == TaskState.CANCELLING:
                    fin_state = TaskState.CANCELLED
                elif exc:
                    fin_state = TaskState.FAILED
                else:
                    fin_state = TaskState.SUCCEEDED

                fin_snap = TaskSnapshot(
                    task_id=t_id,
                    task_type=spec.task_type,
                    state=fin_state,
                    worker_id=snap.worker_id,
                    lease_id=snap.lease_id,
                    fencing_epoch=snap.fencing_epoch,
                    submitted_at=snap.submitted_at,
                    started_at=snap_running.started_at,
                    completed_at=fin_str,
                    result=result,
                    error_message=str(exc) if exc else None,
                )
                self._snapshots[t_id] = fin_snap

        if spec.process_isolated:
            self.process_executor.submit(spec, completion_callback=_completion_cb)
        else:
            self.thread_executor.submit(spec, completion_callback=_completion_cb)

    def cancel_task(self, task_id: str, reason: str = "Cancellation requested") -> TaskSnapshot:
        with self._lock:
            snap = self._snapshots.get(task_id)
            if not snap:
                raise TaskNotFoundError(task_id)

            if snap.is_terminal:
                return snap

            validate_task_transition(task_id, snap.state, TaskState.CANCELLING)
            spec = self._specs.get(task_id)

            if spec and not spec.allow_cancellation:
                from akaalEngine.runtime.models.errors import CancellationUnsupportedError
                raise CancellationUnsupportedError(task_id)

            snap_cancelling = TaskSnapshot(
                task_id=task_id,
                task_type=snap.task_type,
                state=TaskState.CANCELLING,
                worker_id=snap.worker_id,
                lease_id=snap.lease_id,
                fencing_epoch=snap.fencing_epoch,
                submitted_at=snap.submitted_at,
                started_at=snap.started_at,
            )
            self._snapshots[task_id] = snap_cancelling

            # Trigger cancellation in executors
            self.thread_executor.cancel(task_id, reason)
            self.process_executor.cancel(task_id)

            now_str = datetime.now(timezone.utc).isoformat()
            snap_cancelled = TaskSnapshot(
                task_id=task_id,
                task_type=snap.task_type,
                state=TaskState.CANCELLED,
                worker_id=snap.worker_id,
                lease_id=snap.lease_id,
                fencing_epoch=snap.fencing_epoch,
                submitted_at=snap.submitted_at,
                started_at=snap.started_at,
                completed_at=now_str,
                error_message=f"Cancelled: {reason}",
            )
            self._snapshots[task_id] = snap_cancelled
            return snap_cancelled

    def pause_task(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            snap = self._snapshots.get(task_id)
            if not snap:
                raise TaskNotFoundError(task_id)

            spec = self._specs.get(task_id)
            if spec and not spec.allow_pause:
                raise PauseUnsupportedError(task_id)

            validate_task_transition(task_id, snap.state, TaskState.PAUSED)
            self.thread_executor.pause(task_id)

            snap_paused = TaskSnapshot(
                task_id=task_id,
                task_type=snap.task_type,
                state=TaskState.PAUSED,
                worker_id=snap.worker_id,
                lease_id=snap.lease_id,
                fencing_epoch=snap.fencing_epoch,
                submitted_at=snap.submitted_at,
                started_at=snap.started_at,
            )
            self._snapshots[task_id] = snap_paused
            return snap_paused

    def resume_task(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            snap = self._snapshots.get(task_id)
            if not snap:
                raise TaskNotFoundError(task_id)

            validate_task_transition(task_id, snap.state, TaskState.RUNNING)
            self.thread_executor.resume(task_id)

            snap_running = TaskSnapshot(
                task_id=task_id,
                task_type=snap.task_type,
                state=TaskState.RUNNING,
                worker_id=snap.worker_id,
                lease_id=snap.lease_id,
                fencing_epoch=snap.fencing_epoch,
                submitted_at=snap.submitted_at,
                started_at=snap.started_at,
            )
            self._snapshots[task_id] = snap_running
            return snap_running

    def inspect_task(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            snap = self._snapshots.get(task_id)
            if not snap:
                raise TaskNotFoundError(task_id)
            return snap

    # --- Worker Management ---
    def register_worker(self, spec: WorkerSpec) -> WorkerSnapshot:
        with self._lock:
            return self.registry.register_worker(spec)

    def unregister_worker(self, worker_id: str, reason: str = "voluntary") -> None:
        with self._lock:
            self.registry.deregister_worker(worker_id, reason)

    def inspect_worker(self, worker_id: str) -> WorkerSnapshot:
        with self._lock:
            return self.registry.get_snapshot(worker_id)

    # --- Execution Lease & Fencing Management ---
    def acquire_execution_lease(self, task_id: str, worker_id: str, ttl_seconds: Optional[float] = None, fencing_epoch: Optional[int] = None) -> ExecutionLease:
        with self._lock:
            return self.lease_manager.acquire_lease(task_id, worker_id, ttl_seconds=ttl_seconds, fencing_epoch=fencing_epoch)

    def renew_execution_lease(self, lease_id: str, ttl_seconds: Optional[float] = None) -> ExecutionLease:
        with self._lock:
            return self.lease_manager.renew_lease(lease_id, ttl_seconds=ttl_seconds)

    def release_execution_lease(self, lease_id: str) -> None:
        with self._lock:
            self.lease_manager.release_lease(lease_id)

    # --- Recovery ---
    def recover_runtime_state(self, migration_id: str) -> RuntimeRecoveryPlan:
        with self._lock:
            return self.recovery_coordinator.evaluate_recovery(migration_id)

    # --- Drain Management ---
    def set_drain_mode(self, is_draining: bool) -> None:
        with self._lock:
            self.admission_controller.set_draining(is_draining)
            logger.info("[RuntimeAuthority] Drain mode set to %s", is_draining)

    @property
    def is_draining(self) -> bool:
        with self._lock:
            return self.admission_controller.is_draining

    # --- Runtime Snapshot ---
    def get_runtime_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            workers = self.registry.list_snapshots()
            tasks = [snap.to_dict() for snap in self._snapshots.values()]
            utilization = self.admission_controller.get_utilization()

            return {
                "is_running": self._is_running,
                "is_shutting_down": self._is_shutting_down,
                "is_draining": self.admission_controller.is_draining,
                "active_workers": [w.to_dict() for w in workers],
                "task_snapshots": tasks,
                "resource_utilization": utilization,
                "adaptive_workers": self.adaptive_controller.current_workers,
            }

