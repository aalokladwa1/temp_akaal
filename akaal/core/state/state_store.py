"""
AKAAL Enterprise Platform — Centralized State Store
===================================================
Authoritative manager for Runtime state, Worker state, Progress, Metrics, Heartbeats, WAL & Checkpoint metadata.
"""

import threading
from typing import Any, Dict, List, Optional
from akaal.core.interfaces.enterprise_interfaces import IStateStore


class CentralStateStore(IStateStore):
    """Centralized Thread-Safe Singleton State Store."""

    _instance: Optional["CentralStateStore"] = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "CentralStateStore":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super(CentralStateStore, cls).__new__(cls)
                    cls._instance._state = {
                        "runtime": {},
                        "worker": {},
                        "migration": {},
                        "governance": {},
                        "progress": {},
                        "metrics": {},
                        "heartbeats": {},
                        "checkpoint": {},
                        "wal": {},
                    }
                    cls._instance._lock = threading.Lock()
        return cls._instance

    def set_state(self, key: str, value: Any, category: str = "runtime") -> None:
        with self._lock:
            if category not in self._state:
                self._state[category] = {}
            self._state[category][key] = value

    def get_state(self, key: str, default: Any = None, category: str = "runtime") -> Any:
        with self._lock:
            return self._state.get(category, {}).get(key, default)

    def update_progress(self, migration_id: str, progress_data: Dict[str, Any]) -> None:
        with self._lock:
            self._state["progress"][migration_id] = progress_data

    def get_progress(self, migration_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._state["progress"].get(migration_id, {
                "migration_id": migration_id,
                "rows_migrated": 0,
                "rows_validated": 0,
                "percentage": 0.0,
                "status": "CREATED"
            })

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {cat: dict(val) for cat, val in self._state.items()}
