"""
ClusterScheduler facade module for Distributed Runtime (Platform 2).
Coordinates task scheduling across cluster workers using pluggable SchedulingPolicy instances.
"""

from typing import Optional, Dict, Any, List
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import TaskId, WorkerId
from akaal.distributed.domain.models import Task, Worker, SchedulerDecision
from akaal.distributed.domain.errors import SchedulerError, WorkerUnavailableError
from akaal.distributed.scheduler.selector import WorkerSelector
from akaal.distributed.scheduler.policy import (
    SchedulingPolicy,
    FIFOSchedulingPolicy,
    LeastLoadedSchedulingPolicy,
)
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher, TaskAssigned

logger = logging.getLogger("nexusforge.distributed.scheduler")


class ClusterScheduler:
    """
    ClusterScheduler facade responsible for task-to-worker scheduling decisions.
    """

    def __init__(

        self,
        worker_selector: WorkerSelector,
        publisher: EventPublisher,
        policy: Optional[SchedulingPolicy] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._selector = worker_selector
        self._publisher = publisher
        self._policy = policy or LeastLoadedSchedulingPolicy()
        self._clock = clock or SystemClock()

    def set_policy(self, policy: SchedulingPolicy) -> None:
        with self._lock:
            self._policy = policy

    def schedule_task(self, task: Task) -> SchedulerDecision:
        """Schedule task to an eligible candidate worker."""
        with self._lock:
            candidates = self._selector.select_candidates(task)
            now = self._clock.now_timestamp()

            if not candidates:
                logger.warning(f"No eligible workers found for task '{task.task_id}'.")
                return SchedulerDecision(
                    task_id=task.task_id,
                    target_worker_id=None,
                    policy_name=type(self._policy).__name__,
                    decision_reason="No eligible workers available.",
                    decision_timestamp=now,
                )

            target_worker = self._policy.select_worker(task, candidates)
            if target_worker is None:
                return SchedulerDecision(
                    task_id=task.task_id,
                    target_worker_id=None,
                    policy_name=type(self._policy).__name__,
                    decision_reason="SchedulingPolicy returned no worker.",
                    decision_timestamp=now,
                )

            t_str = str(task.task_id)
            w_str = str(target_worker.worker_id)

            self._publisher.publish(
                TaskAssigned(
                    task_id=t_str,
                    worker_id=w_str,
                )
            )

            return SchedulerDecision(
                task_id=task.task_id,
                target_worker_id=target_worker.worker_id,
                policy_name=type(self._policy).__name__,
                decision_reason="Worker selected successfully.",
                decision_timestamp=now,
            )
