"""
akaalEngine.runtime.distributed.coordinator
============================================
Distributed Execution Coordinator & Leader Election Coordinator backed by Durability CAS / Fencing.
Conserves node coordination & cluster leadership semantics mined from `akaal/distributed/`.
"""

import logging
from threading import RLock
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("akaalEngine.runtime.distributed")


class LeaderElectionCoordinator:
    """
    Durability-backed or in-memory CAS Leader Election Coordinator.
    Enforces active leader node identity and generation epoch.
    """

    def __init__(self, node_id: str, lease_ttl_seconds: float = 15.0) -> None:
        self.node_id = node_id
        self.lease_ttl_seconds = lease_ttl_seconds
        self._current_leader: Optional[str] = None
        self._leader_epoch: int = 0
        self._lease_expires_at: float = 0.0
        self._lock = RLock()

    def attempt_claim_leadership(self) -> bool:
        with self._lock:
            now = time.time()
            if self._current_leader is None or now >= self._lease_expires_at:
                self._current_leader = self.node_id
                self._leader_epoch += 1
                self._lease_expires_at = now + self.lease_ttl_seconds
                logger.info(f"[LeaderElection] Node '{self.node_id}' claimed leadership (epoch={self._leader_epoch}).")
                return True
            elif self._current_leader == self.node_id:
                self._lease_expires_at = now + self.lease_ttl_seconds
                return True
            return False

    @property
    def is_leader(self) -> bool:
        with self._lock:
            return self._current_leader == self.node_id and time.time() < self._lease_expires_at

    def get_leader_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "leader_id": self._current_leader,
                "leader_epoch": self._leader_epoch,
                "is_active_leader": self.is_leader,
                "lease_expires_at": self._lease_expires_at,
            }


class DistributedCoordinator:
    """
    Distributed Execution Coordinator tracking cluster nodes, topology, and execution routing seams.
    """

    def __init__(self, local_node_id: str = "node-local") -> None:
        self.local_node_id = local_node_id
        self.leader_coordinator = LeaderElectionCoordinator(local_node_id)
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

        # Register local node
        self.register_node(local_node_id, address="127.0.0.1", port=9000)

    def register_node(self, node_id: str, address: str, port: int) -> None:
        with self._lock:
            self._nodes[node_id] = {
                "node_id": node_id,
                "address": address,
                "port": port,
                "status": "ONLINE",
                "registered_at": time.time(),
                "last_seen": time.time(),
            }

    def list_nodes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._nodes.values())
