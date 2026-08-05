"""
AKAAL Enterprise Platform — Runtime Registry
=============================================
Single source of truth for runtime IDs, migration IDs, PIDs, worker leases, heartbeats, WAL & Checkpoint pointers.
"""

import time
import threading
from typing import Any, Dict, List, Optional
from akaal.core.interfaces.enterprise_interfaces import IRuntimeRegistry


class RuntimeRegistry(IRuntimeRegistry):
    """Authoritative Runtime Registry."""

    def __init__(self) -> None:
        self._runtimes: Dict[str, Dict[str, Any]] = {}
        self._migration_map: Dict[str, str] = {}
        self._lock = threading.Lock()

    def register_runtime(self, runtime_id: str, migration_id: str, pid: int, metadata: Dict[str, Any]) -> None:
        with self._lock:
            entry = {
                "runtime_id": runtime_id,
                "migration_id": migration_id,
                "pid": pid,
                "status": "RUNNING",
                "last_heartbeat": time.time(),
                "wal_pointer": metadata.get("wal_pointer", "wal-00001"),
                "checkpoint_pointer": metadata.get("checkpoint_pointer", "chk-00001"),
                "lease_token": f"lease-{runtime_id}-{int(time.time())}",
                "metadata": metadata,
            }
            self._runtimes[runtime_id] = entry
            self._migration_map[migration_id] = runtime_id

    def unregister_runtime(self, runtime_id: str) -> None:
        with self._lock:
            entry = self._runtimes.pop(runtime_id, None)
            if entry:
                self._migration_map.pop(entry["migration_id"], None)

    def get_runtime(self, runtime_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._runtimes.get(runtime_id)

    def get_runtime_by_migration(self, migration_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rid = self._migration_map.get(migration_id)
            return self._runtimes.get(rid) if rid else None

    def update_heartbeat(self, runtime_id: str) -> None:
        with self._lock:
            if runtime_id in self._runtimes:
                self._runtimes[runtime_id]["last_heartbeat"] = time.time()

    def list_runtimes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._runtimes.values())
