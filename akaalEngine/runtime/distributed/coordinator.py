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


import os
import socket
import hashlib

def resolve_stable_node_id() -> str:
    """
    Dynamically resolves a stable node identity representing the AKAAL Service Installation on a host.
    Precedence:
    1. Explicit enterprise configuration via `AKAAL_NODE_ID` environment variable (if non-empty).
    2. Deterministic hash of hostname, installation directory path, and OS environment.
    """
    machine_sig = os.environ.get("AKAAL_NODE_ID", "").strip()
    if machine_sig:
        return machine_sig
    hostname = socket.gethostname() or "localhost"
    install_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    seed = f"{hostname}::{install_root}::{os.name}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"node-{hostname}-{h}"


class DistributedCoordinator:
    """
    Distributed Execution Coordinator tracking cluster nodes, topology, and execution routing seams.
    """

    def __init__(self, local_node_id: Optional[str] = None) -> None:
        self.local_node_id = local_node_id or resolve_stable_node_id()
        self.leader_coordinator = LeaderElectionCoordinator(self.local_node_id)
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

        # Register local node
        self.register_node(self.local_node_id, address="127.0.0.1", port=9000)

    def register_node(self, node_id: str, address: str, port: int, capabilities: Optional[List[str]] = None) -> None:
        with self._lock:
            now = time.time()
            self._nodes[node_id] = {
                "node_id": node_id,
                "address": address,
                "port": port,
                "status": "ONLINE",
                "drain_state": "ACTIVE",
                "capabilities": list(capabilities or []),
                "registered_at": now,
                "last_seen": now,
            }

    def heartbeat(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id]["last_seen"] = time.time()
                if self._nodes[node_id]["status"] == "DEAD":
                    self._nodes[node_id]["status"] = "ONLINE"
                return True
            return False

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            node = self._nodes.get(node_id)
            return dict(node) if node else None

    def set_node_drain_state(self, node_id: str, drain_state: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id]["drain_state"] = drain_state
                self._nodes[node_id]["last_seen"] = time.time()
                return True
            return False

    def set_node_status(self, node_id: str, status: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id]["status"] = status
                self._nodes[node_id]["last_seen"] = time.time()
                return True
            return False

    def list_nodes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(n) for n in self._nodes.values()]

