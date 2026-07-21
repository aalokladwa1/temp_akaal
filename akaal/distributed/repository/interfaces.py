"""
Storage-Agnostic Repository Interfaces for Enterprise Distributed Runtime.
Follows Clean Architecture and Dependency Inversion.
"""

from abc import ABC, abstractmethod
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


class WorkerRepository(ABC):
    """Storage-agnostic repository for Worker tracking."""

    @abstractmethod
    def save_worker(self, worker: Worker) -> None: pass

    @abstractmethod
    def get_worker(self, worker_id: WorkerId) -> Optional[Worker]: pass

    @abstractmethod
    def update_worker(self, worker: Worker) -> None: pass

    @abstractmethod
    def delete_worker(self, worker_id: WorkerId) -> None: pass

    @abstractmethod
    def list_workers(
        self,
        status: Optional[WorkerStatus] = None,
        health: Optional[WorkerHealth] = None,
    ) -> List[Worker]: pass


class ClusterRepository(ABC):
    """Storage-agnostic repository for Cluster metadata and snapshots."""

    @abstractmethod
    def save_cluster(self, cluster: Cluster) -> None: pass

    @abstractmethod
    def get_cluster(self, cluster_id: ClusterId) -> Optional[Cluster]: pass

    @abstractmethod
    def update_cluster(self, cluster: Cluster) -> None: pass

    @abstractmethod
    def save_snapshot(self, snapshot: ClusterSnapshot) -> None: pass

    @abstractmethod
    def get_latest_snapshot(self, cluster_id: ClusterId) -> Optional[ClusterSnapshot]: pass


class TaskRepository(ABC):
    """Storage-agnostic repository for Task and Assignment persistence."""

    @abstractmethod
    def save_task(self, task: Task) -> None: pass

    @abstractmethod
    def get_task(self, task_id: TaskId) -> Optional[Task]: pass

    @abstractmethod
    def update_task(self, task: Task) -> None: pass

    @abstractmethod
    def delete_task(self, task_id: TaskId) -> None: pass

    @abstractmethod
    def save_assignment(self, assignment: Assignment) -> None: pass

    @abstractmethod
    def get_assignment(self, task_id: TaskId) -> Optional[Assignment]: pass

    @abstractmethod
    def update_assignment(self, assignment: Assignment) -> None: pass

    @abstractmethod
    def list_assignments(self, worker_id: Optional[WorkerId] = None) -> List[Assignment]: pass


class LeaseRepository(ABC):
    """Storage-agnostic repository for Lease tracking."""

    @abstractmethod
    def save_lease(self, lease: Lease) -> None: pass

    @abstractmethod
    def get_lease(self, lease_id: LeaseId) -> Optional[Lease]: pass

    @abstractmethod
    def get_lease_by_task(self, task_id: TaskId) -> Optional[Lease]: pass

    @abstractmethod
    def update_lease(self, lease: Lease) -> None: pass

    @abstractmethod
    def delete_lease(self, lease_id: LeaseId) -> None: pass

    @abstractmethod
    def list_active_leases() -> List[Lease]: pass


class MembershipRepository(ABC):
    """Storage-agnostic repository for ClusterMembership tracking."""

    @abstractmethod
    def save_membership(self, membership: ClusterMembership) -> None: pass

    @abstractmethod
    def get_membership(self, cluster_id: ClusterId) -> Optional[ClusterMembership]: pass

    @abstractmethod
    def update_membership(self, membership: ClusterMembership) -> None: pass
