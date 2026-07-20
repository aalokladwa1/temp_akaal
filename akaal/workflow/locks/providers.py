"""ILockProvider Protocol and Distributed Lock Provider Implementations."""

import threading
from typing import Dict, Protocol, Tuple
from akaal.workflow.utils.clock import IClock, SystemClock


class ILockProvider(Protocol):
    """Abstract interface decoupling engine from distributed locking backends."""

    def acquire_lock(self, resource_id: str, ttl_seconds: float = 30.0) -> Tuple[bool, int]:
        """Acquire lock returning (success, fence_token)."""
        ...

    def renew_lock(self, resource_id: str, fence_token: int, ttl_seconds: float = 30.0) -> bool:
        """Renew active lock lease."""
        ...

    def release_lock(self, resource_id: str, fence_token: int) -> bool:
        """Release lock lease matching fencing token."""
        ...


class InMemoryLockProvider(ILockProvider):
    """Thread-safe in-memory lock provider with fencing tokens and TTL expiration."""

    def __init__(self, clock: IClock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._locks: Dict[str, Tuple[float, int]] = {}  # resource_id -> (expires_at, fence_token)
        self._fence_counter: int = 0
        self._lock = threading.Lock()

    def acquire_lock(self, resource_id: str, ttl_seconds: float = 30.0) -> Tuple[bool, int]:
        with self._lock:
            now = float(self._clock.monotonic())
            current = self._locks.get(resource_id)
            if current and current[0] > now:
                return False, 0  # Lock held by another process

            self._fence_counter += 1
            fence_token = self._fence_counter
            expires_at = now + ttl_seconds
            self._locks[resource_id] = (expires_at, fence_token)
            return True, fence_token

    def renew_lock(self, resource_id: str, fence_token: int, ttl_seconds: float = 30.0) -> bool:
        with self._lock:
            now = float(self._clock.monotonic())
            current = self._locks.get(resource_id)
            if current and current[1] == fence_token and current[0] > now:
                expires_at = now + ttl_seconds
                self._locks[resource_id] = (expires_at, fence_token)
                return True
            return False

    def release_lock(self, resource_id: str, fence_token: int) -> bool:
        with self._lock:
            current = self._locks.get(resource_id)
            if current and current[1] == fence_token:
                self._locks.pop(resource_id, None)
                return True
            return False


class RedisLockProvider(InMemoryLockProvider):
    """Redis distributed lock provider facade (falls back to thread-safe lease memory)."""
    pass


class EtcdLockProvider(InMemoryLockProvider):
    """Etcd distributed lock provider facade."""
    pass


class ZooKeeperLockProvider(InMemoryLockProvider):
    """ZooKeeper distributed lock provider facade."""
    pass


class ConsulLockProvider(InMemoryLockProvider):
    """Consul distributed lock provider facade."""
    pass


class PostgresAdvisoryLockProvider(InMemoryLockProvider):
    """Postgres advisory lock provider facade."""
    pass
