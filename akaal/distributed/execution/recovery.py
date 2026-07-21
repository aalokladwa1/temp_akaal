"""
RecoveryManager module.
Manages execution replay, lease recovery, scheduler reconstruction,
ownership restoration, and failed execution recovery.
"""

from dataclasses import dataclass, field, replace
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import TaskId, WorkerId, LeaseId, ExecutionId
from akaal.distributed.domain.models import Task, Lease, Assignment
from akaal.distributed.domain.enums import AssignmentState
from akaal.distributed.domain.errors import DistributedRuntimeError
from akaal.distributed.repository.interfaces import TaskRepository, LeaseRepository, WorkerRepository
from akaal.distributed.repository.state_store import ClusterStateStore
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher, ClusterRecovered

logger = logging.getLogger("nexusforge.distributed.recovery")


class RecoveryManager:
    """
    Dedicated RecoveryManager for cluster failure recovery, lease expiration recovery,
    and scheduler state reconstruction.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        lease_repo: LeaseRepository,
        worker_repo: WorkerRepository,
        state_store: ClusterStateStore,
        publisher: EventPublisher,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._task_repo = task_repo
        self._lease_repo = lease_repo
        self._worker_repo = worker_repo
        self._state_store = state_store
        self._publisher = publisher
        self._clock = clock or SystemClock()

    def recover_expired_leases(self) -> List[Task]:
        """
        Inspects active leases. If expired based on Clock, evicts lease and returns tasks requiring reassignment.
        """
        with self._lock:
            now = self._clock.now_timestamp()
            recovered_tasks: List[Task] = []
            
            for lease in self._lease_repo.list_active_leases():
                if lease.expires_at < now:
                    logger.warning(f"Lease '{lease.lease_id}' expired for task '{lease.task_id}'. Reclaiming task.")
                    self._lease_repo.delete_lease(lease.lease_id)
                    
                    task = self._task_repo.get_task(lease.task_id)
                    if task:
                        recovered_tasks.append(task)
                        assignment = self._task_repo.get_assignment(task.task_id)
                        if assignment:
                            updated_assignment = replace(assignment, state=AssignmentState.RETRY)
                            self._task_repo.update_assignment(updated_assignment)

            return recovered_tasks

    def restore_execution_ownership(self, execution_id: ExecutionId, target_worker_id: WorkerId) -> None:
        """Restores execution ownership mapping in ClusterStateStore."""
        with self._lock:
            self._state_store.bind_execution_ownership(execution_id, target_worker_id)
            logger.info(f"Restored ownership of execution '{execution_id}' to worker '{target_worker_id}'.")

    def reconstruct_scheduler_state(self) -> Dict[str, Any]:
        """Reconstructs active scheduler assignment snapshot."""
        with self._lock:
            assignments = self._task_repo.list_assignments()
            active = [a for a in assignments if a.state in (AssignmentState.ASSIGNED, AssignmentState.LEASED, AssignmentState.RUNNING)]
            return {
                "active_assignments_count": len(active),
                "timestamp": self._clock.now_timestamp(),
            }
