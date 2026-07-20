"""Raft/SWIM Leader Election Protocol Implementation."""

import threading
from typing import Optional
from akaal.workflow.locks.providers import ILockProvider, InMemoryLockProvider
from akaal.workflow.utils.clock import IClock, SystemClock


class RaftLeaderElector:
    """Thread-safe leader elector managing active cluster leader state."""

    def __init__(
        self,
        node_id: str,
        lock_provider: ILockProvider | None = None,
        clock: IClock | None = None,
    ) -> None:
        self.node_id = node_id
        self._lock_provider = lock_provider or InMemoryLockProvider()
        self._clock = clock or SystemClock()
        self._is_leader: bool = False
        self._fence_token: int = 0
        self._lock = threading.Lock()

    def campaign(self) -> bool:
        """Campaign for cluster leadership."""
        with self._lock:
            success, token = self._lock_provider.acquire_lock("cluster_leader_lease", ttl_seconds=5.0)
            if success:
                self._is_leader = True
                self._fence_token = token
                return True
            self._is_leader = False
            return False

    def renew_leadership(self) -> bool:
        """Renew active leadership lease."""
        with self._lock:
            if not self._is_leader:
                return False
            success = self._lock_provider.renew_lock("cluster_leader_lease", self._fence_token, ttl_seconds=5.0)
            if not success:
                self._is_leader = False
            return success

    @property
    def is_leader(self) -> bool:
        with self._lock:
            return self._is_leader
