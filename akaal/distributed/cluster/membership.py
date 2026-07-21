"""
ClusterMembershipService module.
Manages cluster nodes, workers, quorum state, and membership consistency snapshots.
"""

from threading import RLock
from typing import Dict, Any, Optional, List
import logging

from akaal.distributed.domain.identifiers import ClusterId, NodeId, WorkerId
from akaal.distributed.domain.models import ClusterMembership, Node, Worker
from akaal.distributed.domain.errors import MembershipError
from akaal.distributed.repository.interfaces import MembershipRepository
from akaal.distributed.events.events import EventPublisher

logger = logging.getLogger("nexusforge.distributed.membership")


class ClusterMembershipService:
    """
    Thread-safe ClusterMembershipService.
    Manages node/worker join/leave, quorum size verification, and membership snapshots.
    """

    def __init__(self, repository: MembershipRepository, publisher: EventPublisher) -> None:
        self._lock = RLock()
        self._repository = repository
        self._publisher = publisher

    def get_or_create_membership(self, cluster_id: ClusterId, quorum_size: int = 1) -> ClusterMembership:
        with self._lock:
            mem = self._repository.get_membership(cluster_id)
            if mem is None:
                mem = ClusterMembership(
                    cluster_id=cluster_id,
                    nodes={},
                    workers={},
                    quorum_size=quorum_size,
                    cluster_version=1,
                )
                self._repository.save_membership(mem)
            return mem

    def join_node(self, cluster_id: ClusterId, node: Node) -> ClusterMembership:
        with self._lock:
            mem = self.get_or_create_membership(cluster_id)
            nodes = dict(mem.nodes)
            nodes[str(node.node_id)] = node
            
            updated = ClusterMembership(
                cluster_id=cluster_id,
                nodes=nodes,
                workers=mem.workers,
                quorum_size=mem.quorum_size,
                cluster_version=mem.cluster_version + 1,
            )
            self._repository.update_membership(updated)
            return updated

    def leave_node(self, cluster_id: ClusterId, node_id: NodeId) -> ClusterMembership:
        with self._lock:
            mem = self.get_or_create_membership(cluster_id)
            nodes = dict(mem.nodes)
            nodes.pop(str(node_id), None)

            updated = ClusterMembership(
                cluster_id=cluster_id,
                nodes=nodes,
                workers=mem.workers,
                quorum_size=mem.quorum_size,
                cluster_version=mem.cluster_version + 1,
            )
            self._repository.update_membership(updated)
            return updated

    def is_quorum_satisfied(self, cluster_id: ClusterId) -> bool:
        with self._lock:
            mem = self.get_or_create_membership(cluster_id)
            active_nodes = len([n for n in mem.nodes.values() if n.status == "ACTIVE"])
            return active_nodes >= mem.quorum_size
