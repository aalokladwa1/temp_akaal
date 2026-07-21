"""
ElectionService and LeadershipService modules.
Implements leader election, leadership transfer, failover, and split-brain prevention.
"""

from abc import ABC, abstractmethod
from threading import RLock
from typing import Optional, Dict, Any
import logging

from akaal.distributed.domain.identifiers import ClusterId, NodeId
from akaal.distributed.domain.errors import LeaderElectionError
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher, LeaderChanged
from akaal.distributed.cluster.membership import ClusterMembershipService

logger = logging.getLogger("nexusforge.distributed.leader")


class ElectionService(ABC):
    """Abstract ElectionService interface."""

    @abstractmethod
    def run_election(self, cluster_id: ClusterId, candidate_node_id: NodeId) -> bool:
        pass

    @abstractmethod
    def get_leader(self, cluster_id: ClusterId) -> Optional[NodeId]:
        pass


class LeadershipService:
    """
    LeadershipService managing leader state, leadership transfers, failovers, and split-brain checks.
    """

    def __init__(
        self,
        membership_service: ClusterMembershipService,
        publisher: EventPublisher,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._membership_service = membership_service
        self._publisher = publisher
        self._clock = clock or SystemClock()
        self._leaders: Dict[str, NodeId] = {}  # cluster_id -> leader NodeId
        self._term: Dict[str, int] = {}  # cluster_id -> term

    def run_election(self, cluster_id: ClusterId, candidate_node_id: NodeId) -> bool:
        """
        Run leader election with split-brain prevention via quorum verification.
        """
        with self._lock:
            # Split-brain check: Quorum MUST be satisfied before electing leader
            if not self._membership_service.is_quorum_satisfied(cluster_id):
                logger.error(f"Leader election failed for cluster '{cluster_id}': Quorum not satisfied (split-brain prevention).")
                raise LeaderElectionError(f"Cannot elect leader for '{cluster_id}': Quorum state degraded.")

            current_leader = self._leaders.get(str(cluster_id))
            if current_leader and current_leader != candidate_node_id:
                # Leadership exists
                return False

            old_leader_str = str(current_leader) if current_leader else ""
            self._leaders[str(cluster_id)] = candidate_node_id
            self._term[str(cluster_id)] = self._term.get(str(cluster_id), 0) + 1

            c_id = str(cluster_id)
            new_leader_str = str(candidate_node_id)
            
            logger.info(f"Node '{new_leader_str}' elected leader of cluster '{c_id}'.")
            self._publisher.publish(
                LeaderChanged(
                    cluster_id=c_id,
                    old_leader_node_id=old_leader_str,
                    new_leader_node_id=new_leader_str,
                )
            )
            return True

    def get_leader(self, cluster_id: ClusterId) -> Optional[NodeId]:
        with self._lock:
            return self._leaders.get(str(cluster_id))

    def transfer_leadership(self, cluster_id: ClusterId, target_node_id: NodeId) -> bool:
        """Voluntarily transfer leadership to target_node_id."""
        with self._lock:
            old_leader = self._leaders.get(str(cluster_id))
            if old_leader:
                self._leaders.pop(str(cluster_id), None)
            return self.run_election(cluster_id, target_node_id)

    def handle_leader_failure(self, cluster_id: ClusterId) -> None:
        """Clear failed leader to allow re-election."""
        with self._lock:
            old_leader = self._leaders.pop(str(cluster_id), None)
            if old_leader:
                logger.warning(f"Leader '{old_leader}' for cluster '{cluster_id}' failed. Cleared leader state for failover.")
