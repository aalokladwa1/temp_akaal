"""
Centralized ClusterStateStore for Distributed Runtime (Platform 2).
Centralizes cluster snapshots, leader info, worker state, execution ownership,
and cluster state versioning.
"""

from threading import RLock
from typing import Optional, List, Dict, Any

from akaal.distributed.domain.identifiers import ClusterId, NodeId, WorkerId, TaskId, ExecutionId
from akaal.distributed.domain.enums import ClusterState, WorkerStatus, WorkerHealth
from akaal.distributed.domain.models import Cluster, Worker, ClusterMembership, ClusterSnapshot
from akaal.distributed.domain.errors import ClusterStateError
from akaal.distributed.repository.interfaces import (
    WorkerRepository,
    ClusterRepository,
    MembershipRepository,
)


class ClusterStateStore:
    """
    Thread-safe Centralized ClusterStateStore.
    Maintains centralized snapshots, leader ownership, worker registries, and versioning.
    """

    def __init__(
        self,
        cluster_repo: ClusterRepository,
        worker_repo: WorkerRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        self._lock = RLock()
        self._cluster_repo = cluster_repo
        self._worker_repo = worker_repo
        self._membership_repo = membership_repo
        self._ownership_map: Dict[str, str] = {}  # execution_id -> worker_id

    def get_cluster_snapshot(self, cluster_id: ClusterId) -> Optional[ClusterSnapshot]:
        with self._lock:
            return self._cluster_repo.get_latest_snapshot(cluster_id)

    def record_snapshot(
        self,
        cluster_id: ClusterId,
        state: ClusterState,
        leader_node_id: Optional[NodeId],
        membership: ClusterMembership,
    ) -> ClusterSnapshot:
        with self._lock:
            latest = self._cluster_repo.get_latest_snapshot(cluster_id)
            next_version = (latest.snapshot_version + 1) if latest else 1
            
            snapshot = ClusterSnapshot(
                cluster_id=cluster_id,
                state=state,
                leader_node_id=leader_node_id,
                membership=membership,
                snapshot_version=next_version,
                timestamp=0.0,
            )
            self._cluster_repo.save_snapshot(snapshot)
            return snapshot

    def bind_execution_ownership(self, execution_id: ExecutionId, worker_id: WorkerId) -> None:
        with self._lock:
            self._ownership_map[str(execution_id)] = str(worker_id)

    def get_execution_owner(self, execution_id: ExecutionId) -> Optional[str]:
        with self._lock:
            return self._ownership_map.get(str(execution_id))

    def unbind_execution_ownership(self, execution_id: ExecutionId) -> None:
        with self._lock:
            self._ownership_map.pop(str(execution_id), None)
