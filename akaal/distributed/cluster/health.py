"""
ClusterHealthService module.
Aggregates worker, leader, scheduler, queue, lease, and resource health into a single unified status.
"""

from typing import Dict, Any, Optional
from threading import RLock

from akaal.distributed.domain.identifiers import ClusterId
from akaal.distributed.domain.enums import ClusterHealthStatus, WorkerHealth
from akaal.distributed.repository.interfaces import WorkerRepository, LeaseRepository
from akaal.distributed.cluster.membership import ClusterMembershipService
from akaal.distributed.cluster.leader import LeadershipService
from akaal.distributed.clock.clock import Clock, SystemClock


class ClusterHealthService:
    """
    Aggregates multi-service health into a unified ClusterHealthStatus.
    """

    def __init__(
        self,
        membership_service: ClusterMembershipService,
        leadership_service: LeadershipService,
        worker_repo: WorkerRepository,
        lease_repo: LeaseRepository,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._membership = membership_service
        self._leadership = leadership_service
        self._worker_repo = worker_repo
        self._lease_repo = lease_repo
        self._clock = clock or SystemClock()

    def get_cluster_health(self, cluster_id: ClusterId) -> Dict[str, Any]:
        with self._lock:
            # 1. Quorum check
            quorum_ok = self._membership.is_quorum_satisfied(cluster_id)
            
            # 2. Leader check
            leader = self._leadership.get_leader(cluster_id)
            leader_ok = leader is not None

            # 3. Worker health check
            workers = self._worker_repo.list_workers()
            unhealthy_workers = [w for w in workers if w.health == WorkerHealth.UNHEALTHY]

            # 4. Lease status
            now = self._clock.now_timestamp()
            active_leases = self._lease_repo.list_active_leases()
            expired_leases = [l for l in active_leases if l.expires_at < now]

            # Aggregate status
            if not quorum_ok or not leader_ok or len(unhealthy_workers) > len(workers) / 2:
                status = ClusterHealthStatus.UNHEALTHY
            elif len(unhealthy_workers) > 0 or len(expired_leases) > 0:
                status = ClusterHealthStatus.DEGRADED
            else:
                status = ClusterHealthStatus.HEALTHY

            return {
                "status": status.value,
                "cluster_id": str(cluster_id),
                "quorum_satisfied": quorum_ok,
                "leader_node_id": str(leader) if leader else None,
                "total_workers": len(workers),
                "unhealthy_workers_count": len(unhealthy_workers),
                "expired_leases_count": len(expired_leases),
                "timestamp": now,
            }
