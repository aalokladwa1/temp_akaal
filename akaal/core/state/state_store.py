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

    def atomic_claim_start(self, key: str, operation_id: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        S4-H10: Atomically transitions key state from eligible pre-start state to START_REQUESTED.
        Guarantees under self._lock that concurrent callers for key resolve to exactly ONE winning caller.
        """
        import datetime
        with self._lock:
            current = self._state.get("runtime", {}).get(key)
            curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""
            if curr_status in ("START_REQUESTED", "STARTING", "RUNNING", "COMPLETED"):
                return False, current or {"status": curr_status, "operation_id": operation_id}

            new_state = {
                "status": "START_REQUESTED",
                "operation_id": operation_id,
                "claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                **(metadata or {})
            }
            if "runtime" not in self._state:
                self._state["runtime"] = {}
            self._state["runtime"][key] = new_state
            return True, new_state

    def guarded_transition_state(self, key: str, expected_current: List[str], target_status: str, update_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        S4-H11: Executes a state transition ONLY if current status is in expected_current list.
        Prevents stale worker or request thread from overwriting RUNNING or FAILED back to STARTING.
        """
        with self._lock:
            current = self._state.get("runtime", {}).get(key)
            curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""
            if curr_status and curr_status not in [s.upper() for s in expected_current]:
                return False

            merged_state = {**current, **(update_data or {}), "status": target_status} if isinstance(current, dict) else {"status": target_status, **(update_data or {})}
            if "runtime" not in self._state:
                self._state["runtime"] = {}
            self._state["runtime"][key] = merged_state
            return True

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {cat: dict(val) for cat, val in self._state.items()}
