"""
CoordinatorService module for Distributed Runtime (Platform 2).
Provides distributed locks, synchronization barriers, ownership negotiation, and coordination messaging.
"""

from threading import RLock
from typing import Dict, Any, List, Optional, Set
import time
import logging

from akaal.distributed.domain.identifiers import WorkerId, ExecutionId
from akaal.distributed.domain.errors import CoordinationError
from akaal.distributed.events.events import EventPublisher

logger = logging.getLogger("nexusforge.distributed.coordination")


class CoordinatorService:
    """
    Thread-safe CoordinatorService for distributed coordination and lock management.
    """

    def __init__(self, publisher: EventPublisher) -> None:
        self._lock = RLock()
        self._publisher = publisher
        self._locks: Dict[str, str] = {}  # lock_name -> owner_id
        self._barriers: Dict[str, Set[str]] = {}  # barrier_name -> set of arrived worker_ids
        self._barrier_capacities: Dict[str, int] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}  # target_worker_id -> messages

    def acquire_lock(self, lock_name: str, owner_id: str) -> bool:
        """Acquire a named lock for an owner."""
        with self._lock:
            current_owner = self._locks.get(lock_name)
            if current_owner is None or current_owner == owner_id:
                self._locks[lock_name] = owner_id
                return True
            return False

    def release_lock(self, lock_name: str, owner_id: str) -> bool:
        """Release a named lock if owned by owner_id."""
        with self._lock:
            current_owner = self._locks.get(lock_name)
            if current_owner == owner_id:
                self._locks.pop(lock_name, None)
                return True
            return False

    def register_barrier(self, barrier_name: str, capacity: int) -> None:
        """Register a synchronization barrier for a given capacity of workers."""
        with self._lock:
            self._barrier_capacities[barrier_name] = capacity
            if barrier_name not in self._barriers:
                self._barriers[barrier_name] = set()

    def wait_barrier(self, barrier_name: str, worker_id: str) -> bool:
        """Arrive at a barrier. Returns True if all workers have arrived."""
        with self._lock:
            if barrier_name not in self._barrier_capacities:
                raise CoordinationError(f"Barrier '{barrier_name}' is not registered.")
            
            capacity = self._barrier_capacities[barrier_name]
            arrived = self._barriers.setdefault(barrier_name, set())
            arrived.add(worker_id)
            
            return len(arrived) >= capacity

    def negotiate_ownership(self, resource_key: str, candidate_id: str) -> bool:
        """Negotiate exclusive ownership of a resource."""
        return self.acquire_lock(f"ownership:{resource_key}", candidate_id)

    def send_coordination_message(self, target_worker_id: str, message: Dict[str, Any]) -> None:
        """Send a coordination message to a worker."""
        with self._lock:
            if target_worker_id not in self._messages:
                self._messages[target_worker_id] = []
            self._messages[target_worker_id].append(message)

    def consume_coordination_messages(self, target_worker_id: str) -> List[Dict[str, Any]]:
        """Retrieve and clear pending messages for a worker."""
        with self._lock:
            msgs = self._messages.get(target_worker_id, [])
            self._messages[target_worker_id] = []
            return msgs
