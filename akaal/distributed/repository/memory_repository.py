"""
Thread-safe In-Memory Repositories for Enterprise Distributed Runtime.
"""

from threading import RLock
from typing import Optional, List, Dict, Any

from akaal.distributed.domain.identifiers import (
    WorkerId,
    NodeId,
    ClusterId,
    TaskId,
    ExecutionId,
    LeaseId,
)
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth
from akaal.distributed.domain.errors import DistributedRuntimeError
from akaal.distributed.domain.models import (
    Worker,
    Node,
    Cluster,
    Task,
    Lease,
    Assignment,
    ClusterMembership,
    ClusterSnapshot,
)
from akaal.distributed.repository.interfaces import (
    WorkerRepository,
    ClusterRepository,
    TaskRepository,
    LeaseRepository,
    MembershipRepository,
)


class InMemoryWorkerRepository(WorkerRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._workers: Dict[str, Worker] = {}

    def save_worker(self, worker: Worker) -> None:
        with self._lock:
            w_id = str(worker.worker_id)
            if w_id in self._workers:
                raise DistributedRuntimeError(f"Worker {w_id} already exists.")
            self._workers[w_id] = worker

    def get_worker(self, worker_id: WorkerId) -> Optional[Worker]:
        with self._lock:
            return self._workers.get(str(worker_id))

    def update_worker(self, worker: Worker) -> None:
        with self._lock:
            w_id = str(worker.worker_id)
            if w_id not in self._workers:
                raise DistributedRuntimeError(f"Worker {w_id} does not exist.")
            self._workers[w_id] = worker

    def delete_worker(self, worker_id: WorkerId) -> None:
        with self._lock:
            w_id = str(worker_id)
            if w_id in self._workers:
                del self._workers[w_id]

    def list_workers(
        self,
        status: Optional[WorkerStatus] = None,
        health: Optional[WorkerHealth] = None,
    ) -> List[Worker]:
        with self._lock:
            result = list(self._workers.values())
            if status is not None:
                result = [w for w in result if w.status == status]
            if health is not None:
                result = [w for w in result if w.health == health]
            return result


class InMemoryClusterRepository(ClusterRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._clusters: Dict[str, Cluster] = {}
        self._snapshots: Dict[str, List[ClusterSnapshot]] = {}

    def save_cluster(self, cluster: Cluster) -> None:
        with self._lock:
            c_id = str(cluster.cluster_id)
            if c_id in self._clusters:
                raise DistributedRuntimeError(f"Cluster {c_id} already exists.")
            self._clusters[c_id] = cluster

    def get_cluster(self, cluster_id: ClusterId) -> Optional[Cluster]:
        with self._lock:
            return self._clusters.get(str(cluster_id))

    def update_cluster(self, cluster: Cluster) -> None:
        with self._lock:
            c_id = str(cluster.cluster_id)
            if c_id not in self._clusters:
                raise DistributedRuntimeError(f"Cluster {c_id} does not exist.")
            self._clusters[c_id] = cluster

    def save_snapshot(self, snapshot: ClusterSnapshot) -> None:
        with self._lock:
            c_id = str(snapshot.cluster_id)
            if c_id not in self._snapshots:
                self._snapshots[c_id] = []
            self._snapshots[c_id].append(snapshot)

    def get_latest_snapshot(self, cluster_id: ClusterId) -> Optional[ClusterSnapshot]:
        with self._lock:
            snaps = self._snapshots.get(str(cluster_id), [])
            return snaps[-1] if snaps else None


class InMemoryTaskRepository(TaskRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: Dict[str, Task] = {}
        self._assignments: Dict[str, Assignment] = {}

    def save_task(self, task: Task) -> None:
        with self._lock:
            t_id = str(task.task_id)
            self._tasks[t_id] = task

    def get_task(self, task_id: TaskId) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(str(task_id))

    def update_task(self, task: Task) -> None:
        with self._lock:
            t_id = str(task.task_id)
            if t_id not in self._tasks:
                raise DistributedRuntimeError(f"Task {t_id} does not exist.")
            self._tasks[t_id] = task

    def delete_task(self, task_id: TaskId) -> None:
        with self._lock:
            t_id = str(task_id)
            self._tasks.pop(t_id, None)

    def save_assignment(self, assignment: Assignment) -> None:
        with self._lock:
            t_id = str(assignment.task_id)
            self._assignments[t_id] = assignment

    def get_assignment(self, task_id: TaskId) -> Optional[Assignment]:
        with self._lock:
            return self._assignments.get(str(task_id))

    def update_assignment(self, assignment: Assignment) -> None:
        with self._lock:
            t_id = str(assignment.task_id)
            self._assignments[t_id] = assignment

    def list_assignments(self, worker_id: Optional[WorkerId] = None) -> List[Assignment]:
        with self._lock:
            if worker_id is None:
                return list(self._assignments.values())
            w_str = str(worker_id)
            return [a for a in self._assignments.values() if str(a.worker_id) == w_str]


class InMemoryLeaseRepository(LeaseRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._leases: Dict[str, Lease] = {}
        self._task_leases: Dict[str, str] = {}

    def save_lease(self, lease: Lease) -> None:
        with self._lock:
            l_id = str(lease.lease_id)
            t_id = str(lease.task_id)
            self._leases[l_id] = lease
            self._task_leases[t_id] = l_id

    def get_lease(self, lease_id: LeaseId) -> Optional[Lease]:
        with self._lock:
            return self._leases.get(str(lease_id))

    def get_lease_by_task(self, task_id: TaskId) -> Optional[Lease]:
        with self._lock:
            l_id = self._task_leases.get(str(task_id))
            return self._leases.get(l_id) if l_id else None

    def update_lease(self, lease: Lease) -> None:
        with self._lock:
            l_id = str(lease.lease_id)
            if l_id not in self._leases:
                raise DistributedRuntimeError(f"Lease {l_id} does not exist.")
            self._leases[l_id] = lease

    def delete_lease(self, lease_id: LeaseId) -> None:
        with self._lock:
            l_id = str(lease_id)
            lease = self._leases.pop(l_id, None)
            if lease:
                self._task_leases.pop(str(lease.task_id), None)

    def list_active_leases(self) -> List[Lease]:
        with self._lock:
            return list(self._leases.values())


class InMemoryMembershipRepository(MembershipRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._memberships: Dict[str, ClusterMembership] = {}

    def save_membership(self, membership: ClusterMembership) -> None:
        with self._lock:
            c_id = str(membership.cluster_id)
            self._memberships[c_id] = membership

    def get_membership(self, cluster_id: ClusterId) -> Optional[ClusterMembership]:
        with self._lock:
            return self._memberships.get(str(cluster_id))

    def update_membership(self, membership: ClusterMembership) -> None:
        with self._lock:
            c_id = str(membership.cluster_id)
            self._memberships[c_id] = membership
