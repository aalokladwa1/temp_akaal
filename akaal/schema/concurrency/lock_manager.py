"""
AKAAL Platform 5 — Concurrency Lock Manager

Provides thread-safe lock hierarchy management for Global Schema, Table-level, and Advisory locks.
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Dict, Optional, Set

from akaal.schema.domain.enums import LockType
from akaal.schema.domain.errors import ConcurrencyError


@dataclass
class LockGrant:
    lock_type: LockType
    target: str
    owner_id: str
    granted_at: float = field(default_factory=time.time)


class SchemaLockManager:
    """Thread-safe multi-level Lock Manager with lock timeout support."""

    def __init__(self, default_timeout_sec: float = 5.0) -> None:
        self._mutex = threading.RLock()
        self.default_timeout_sec = default_timeout_sec
        self._global_lock_owner: Optional[str] = None
        self._table_exclusive_locks: Dict[str, str] = {}  # table_name -> owner_id
        self._table_shared_locks: Dict[str, Set[str]] = {}  # table_name -> set of owner_ids
        self._advisory_locks: Dict[str, str] = {}  # key -> owner_id

    def acquire_global_lock(self, owner_id: str, timeout_sec: Optional[float] = None) -> bool:
        timeout = timeout_sec if timeout_sec is not None else self.default_timeout_sec
        start = time.time()
        while time.time() - start < timeout:
            with self._mutex:
                if self._global_lock_owner is None and not self._table_exclusive_locks and not self._table_shared_locks:
                    self._global_lock_owner = owner_id
                    return True
                if self._global_lock_owner == owner_id:
                    return True
            time.sleep(0.01)
        raise ConcurrencyError(
            message=f"Failed to acquire GLOBAL_SCHEMA lock for owner '{owner_id}' within {timeout}s timeout.",
            recovery_recommendation="Retry operation after existing schema evolution transactions complete."
        )

    def release_global_lock(self, owner_id: str) -> None:
        with self._mutex:
            if self._global_lock_owner == owner_id:
                self._global_lock_owner = None

    def acquire_table_lock(self, table_name: str, owner_id: str, exclusive: bool = True, timeout_sec: Optional[float] = None) -> bool:
        timeout = timeout_sec if timeout_sec is not None else self.default_timeout_sec
        start = time.time()
        while time.time() - start < timeout:
            with self._mutex:
                if self._global_lock_owner is not None and self._global_lock_owner != owner_id:
                    time.sleep(0.01)
                    continue

                if exclusive:
                    cur_ex = self._table_exclusive_locks.get(table_name)
                    cur_sh = self._table_shared_locks.get(table_name, set())
                    if (cur_ex is None or cur_ex == owner_id) and (not cur_sh or cur_sh == {owner_id}):
                        self._table_exclusive_locks[table_name] = owner_id
                        return True
                else:
                    cur_ex = self._table_exclusive_locks.get(table_name)
                    if cur_ex is None or cur_ex == owner_id:
                        if table_name not in self._table_shared_locks:
                            self._table_shared_locks[table_name] = set()
                        self._table_shared_locks[table_name].add(owner_id)
                        return True
            time.sleep(0.01)

        raise ConcurrencyError(
            message=f"Timeout acquiring {'EXCLUSIVE' if exclusive else 'SHARED'} table lock on '{table_name}'.",
            recovery_recommendation="Verify no long-running schema updates are locking table."
        )

    def release_table_lock(self, table_name: str, owner_id: str) -> None:
        with self._mutex:
            if self._table_exclusive_locks.get(table_name) == owner_id:
                del self._table_exclusive_locks[table_name]
            if table_name in self._table_shared_locks:
                self._table_shared_locks[table_name].discard(owner_id)
                if not self._table_shared_locks[table_name]:
                    del self._table_shared_locks[table_name]
