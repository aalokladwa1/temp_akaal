"""
DistributedExecutionEngineV1 module for Platform 2.
Coordinates task queueing, scheduling, lifecycle state transitions, lease acquisition, and recovery.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from threading import RLock
import logging
import time

from akaal.distributed.domain.identifiers import (
    WorkerId,
    NodeId,
    TaskId,
    ExecutionId,
    AttemptId,
    CorrelationId,
    IdempotencyKey,
)
from akaal.distributed.domain.enums import AssignmentState, WorkerStatus
from akaal.distributed.domain.models import (
    Task,
    ExecutionRequest,
    ExecutionResult,
    ExecutionToken,
    Assignment,
)
from akaal.distributed.domain.errors import DistributedRuntimeError, TaskDistributionError
from akaal.distributed.queue.queue import TaskQueue, MemoryTaskQueue
from akaal.distributed.scheduler.scheduler import ClusterScheduler
from akaal.distributed.worker.lease import LeaseManager
from akaal.distributed.worker.registry import WorkerRegistry
from akaal.distributed.execution.lifecycle import ExecutionLifecycleManager
from akaal.distributed.execution.recovery import RecoveryManager
from akaal.distributed.events.events import InProcessEventDispatcher, TaskStarted, TaskCompleted, TaskFailed
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.metrics.metrics import DistributedMetricsCollector, InMemoryDistributedMetricsCollector

logger = logging.getLogger("nexusforge.distributed.engine")


class DistributedExecutionEngineV1(ABC):
    """Abstract DistributedExecutionEngineV1 interface."""

    @abstractmethod
    def submit_execution(self, task: Task, idempotency_key: Optional[IdempotencyKey] = None) -> ExecutionRequest:
        pass

    @abstractmethod
    def process_next_task(self) -> Optional[ExecutionResult]:
        pass


class DefaultDistributedExecutionEngineV1(DistributedExecutionEngineV1):
    """
    Default production implementation of DistributedExecutionEngineV1.
    Coordinates TaskQueue, ClusterScheduler, LeaseManager, ExecutionLifecycleManager,
    and RecoveryManager. Contains ZERO migration logic.
    """

    def __init__(
        self,
        queue: TaskQueue,
        scheduler: ClusterScheduler,
        lease_manager: LeaseManager,
        registry: WorkerRegistry,
        lifecycle_manager: ExecutionLifecycleManager,
        recovery_manager: RecoveryManager,
        dispatcher: InProcessEventDispatcher,
        clock: Optional[Clock] = None,
        metrics: Optional[DistributedMetricsCollector] = None,
    ) -> None:
        self._lock = RLock()
        self.queue = queue
        self.scheduler = scheduler
        self.lease_manager = lease_manager
        self.registry = registry
        self.lifecycle_manager = lifecycle_manager
        self.recovery_manager = recovery_manager
        self.dispatcher = dispatcher
        self.clock = clock or SystemClock()
        self.metrics = metrics or InMemoryDistributedMetricsCollector()

    def submit_execution(self, task: Task, idempotency_key: Optional[IdempotencyKey] = None) -> ExecutionRequest:
        """Submit a task for execution with IdempotencyKey deduplication."""
        with self._lock:
            key = idempotency_key or IdempotencyKey.generate()
            existing = self.queue.get_by_idempotency_key(key)
            if existing:
                logger.info(f"Execution request with IdempotencyKey '{key}' deduplicated.")
                return existing

            exec_id = task.execution_id
            corr_id = CorrelationId.generate()
            request = ExecutionRequest(
                execution_id=exec_id,
                correlation_id=corr_id,
                task=task,
                idempotency_key=key,
                submitted_at=self.clock.now_timestamp(),
            )
            self.queue.enqueue(request)
            return request

    def process_next_task(self) -> Optional[ExecutionResult]:
        """
        Processes next task in queue:
        1. Dequeue request
        2. Schedule worker
        3. Acquire lease
        4. Execute task
        5. Record metrics & complete
        """
        with self._lock:
            request = self.queue.dequeue()
            if request is None:
                return None

            task = request.task
            t_start = self.clock.now_timestamp()

            # Schedule
            decision = self.scheduler.schedule_task(task)
            if decision.target_worker_id is None:
                # Requeue for retry
                logger.warning(f"No worker available for task '{task.task_id}'. Requeueing.")
                self.queue.requeue_for_retry(request, delay_seconds=1.0)
                return None

            target_worker_id = decision.target_worker_id

            # Acquire Lease
            lease = self.lease_manager.acquire_lease(target_worker_id, task.task_id)

            # Create Assignment
            assignment = Assignment(
                task_id=task.task_id,
                worker_id=target_worker_id,
                lease=lease,
                state=AssignmentState.LEASED,
                assigned_at=t_start,
            )

            # Transition state to RUNNING
            assignment = self.lifecycle_manager.transition_assignment(assignment, AssignmentState.RUNNING)

            w_str = str(target_worker_id)
            t_str = str(task.task_id)
            e_str = str(task.execution_id)

            self.dispatcher.publish(
                TaskStarted(
                    task_id=t_str,
                    execution_id=e_str,
                    worker_id=w_str,
                )
            )

            # Execute work (Platform 2 simulates worker dispatch & task completion)
            duration = self.clock.now_timestamp() - t_start
            result = ExecutionResult(
                execution_id=task.execution_id,
                attempt_id=AttemptId.generate(),
                status="SUCCESS",
                output={"executed_by": w_str, "task_name": task.name},
                duration_seconds=duration,
            )

            # Mark completed
            self.lifecycle_manager.transition_assignment(assignment, AssignmentState.SUCCESS)
            self.lease_manager.revoke_lease(lease.lease_id)

            self.metrics.record_task_duration(task.name, duration)

            self.dispatcher.publish(
                TaskCompleted(
                    task_id=t_str,
                    execution_id=e_str,
                    duration_seconds=duration,
                )
            )

            return result
