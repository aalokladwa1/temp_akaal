"""
AKAAL Enterprise Platform — Centralized State Store
===================================================
Authoritative manager for Runtime state, Worker state, Progress, Metrics, Heartbeats, WAL & Checkpoint metadata.
Backed by thread-safe memory cache and cross-process durable SQLite database (`artifacts/state.db`).
"""

import os
import json
import sqlite3
import datetime
import threading
from typing import Any, Dict, List, Optional, Tuple
from akaal.core.interfaces.enterprise_interfaces import IStateStore


class CentralStateStore(IStateStore):
    """Centralized Thread-Safe Singleton & Cross-Process Durable SQLite State Store."""

    _instance: Optional["CentralStateStore"] = None
    _init_lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> "CentralStateStore":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super(CentralStateStore, cls).__new__(cls)
                    if db_path is None:
                        db_dir = os.path.join(os.getcwd(), "artifacts")
                        os.makedirs(db_dir, exist_ok=True)
                        db_path = os.path.join(db_dir, "state.db")
                    cls._instance.db_path = db_path
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
                    cls._instance._local = threading.local()
                    cls._instance._init_db()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        """Closes thread-local database connection cleanly."""
        if hasattr(self, "_local") and hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS central_state (
                category TEXT NOT NULL,
                state_key TEXT NOT NULL,
                val_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (category, state_key)
            )
            """)

    def set_state(self, key: str, value: Any, category: str = "runtime") -> None:
        import dataclasses
        import enum

        def _json_default(obj: Any) -> Any:
            if hasattr(obj, "to_dict") and callable(obj.to_dict):
                return obj.to_dict()
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            if isinstance(obj, enum.Enum):
                return obj.value
            if hasattr(obj, "__dict__"):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable for CentralStateStore")

        val_json = json.dumps(value, default=_json_default) if value is not None else "null"

        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                INSERT INTO central_state (category, state_key, val_json, updated_at)
                VALUES (?, ?, ?, DATETIME('now'))
                ON CONFLICT(category, state_key) DO UPDATE SET
                    val_json=excluded.val_json,
                    updated_at=DATETIME('now')
                """, (category, key, val_json))

            if category not in self._state:
                self._state[category] = {}
            self._state[category][key] = value

    def get_state(self, key: str, default: Any = None, category: str = "runtime") -> Any:
        with self._lock:
            try:
                conn = self._get_connection()
                cur = conn.execute("SELECT val_json FROM central_state WHERE category=? AND state_key=?", (category, key))
                row = cur.fetchone()
                if row and row["val_json"] and row["val_json"] != "null":
                    val = json.loads(row["val_json"])
                    if category not in self._state:
                        self._state[category] = {}
                    self._state[category][key] = val
                    return val
            except Exception:
                pass

            if category in self._state and key in self._state[category]:
                cached = self._state[category][key]
                if cached is not None:
                    return cached

            return default

    def update_progress(self, migration_id: str, progress_data: Dict[str, Any]) -> None:
        self.set_state(migration_id, progress_data, category="progress")

    def update_cdc_telemetry(self, cdc_session_id: str, telemetry_data: Dict[str, Any]) -> None:
        self.set_state(cdc_session_id, telemetry_data, category="cdc_telemetry")

    def get_cdc_telemetry(self, cdc_session_id: str) -> Optional[Dict[str, Any]]:
        val = self.get_state(cdc_session_id, default=None, category="cdc_telemetry")
        if isinstance(val, dict):
            return val
        return None

    def get_category(self, category: str) -> Dict[str, Any]:
        """Retrieves all key-value entries belonging to a specific category."""
        results: Dict[str, Any] = {}
        with self._lock:
            if category in self._state and isinstance(self._state[category], dict):
                results.update(self._state[category])
            try:
                conn = self._get_connection()
                cur = conn.execute("SELECT state_key, val_json FROM central_state WHERE category=?", (category,))
                for row in cur.fetchall():
                    if row["val_json"] and row["val_json"] != "null":
                        try:
                            val = json.loads(row["val_json"])
                            results[row["state_key"]] = val
                        except Exception:
                            pass
            except Exception:
                pass
        return results

    def get_progress(self, migration_id: str) -> Dict[str, Any]:
        val = self.get_state(migration_id, default=None, category="progress")
        if isinstance(val, dict):
            return val
        return {
            "migration_id": migration_id,
            "rows_migrated": 0,
            "rows_validated": 0,
            "percentage": 0.0,
            "status": "CREATED"
        }

    def list_all_progress(self) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            try:
                conn = self._get_connection()
                cur = conn.execute("SELECT state_key, val_json FROM central_state WHERE category='progress'")
                for row in cur.fetchall():
                    if row["val_json"] and row["val_json"] != "null":
                        try:
                            val = json.loads(row["val_json"])
                            if isinstance(val, dict):
                                results.append(val)
                        except Exception:
                            pass
            except Exception:
                pass
            return results

    def atomic_claim_start(self, key: str, operation_id: str, plan_fingerprint: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        S4-H10: Cross-Process SQLite Atomic Start Claim.
        Acquires a SQLite 'BEGIN IMMEDIATE' write reservation across processes BEFORE reading durable state.
        Ensures that exactly ONE process or thread wins the claim across independent connections.
        """
        category = "runtime"
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
            except Exception:
                pass

            try:
                cur = conn.execute("SELECT val_json FROM central_state WHERE category=? AND state_key=?", (category, key))
                row = cur.fetchone()
                current = json.loads(row["val_json"]) if (row and row["val_json"] and row["val_json"] != "null") else None
                if not current and category in self._state:
                    current = self._state[category].get(key)

                curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""
                if curr_status in ("START_REQUESTED", "STARTING", "RUNNING", "COMPLETED"):
                    conn.commit()
                    return False, current or {"status": curr_status, "operation_id": operation_id, "plan_fingerprint": plan_fingerprint}

                new_state = {
                    "status": "START_REQUESTED",
                    "operation_id": operation_id,
                    "plan_fingerprint": plan_fingerprint,
                    "claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    **(metadata or {})
                }
                val_json = json.dumps(new_state)
                conn.execute("""
                INSERT INTO central_state (category, state_key, val_json, updated_at)
                VALUES (?, ?, ?, DATETIME('now'))
                ON CONFLICT(category, state_key) DO UPDATE SET
                    val_json=excluded.val_json,
                    updated_at=DATETIME('now')
                """, (category, key, val_json))
                conn.commit()

                if category not in self._state:
                    self._state[category] = {}
                self._state[category][key] = new_state
                return True, new_state
            except Exception as ex:
                conn.rollback()
                raise ex

    def guarded_transition_state(self, key: str, expected_current: List[str], target_status: str, update_data: Optional[Dict[str, Any]] = None, category: str = "runtime") -> bool:
        """
        S4-H11: Legal state transition guard backed by cross-process SQLite 'BEGIN IMMEDIATE' transaction.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
            except Exception:
                pass

            try:
                cur = conn.execute("SELECT val_json FROM central_state WHERE category=? AND state_key=?", (category, key))
                row = cur.fetchone()
                current = json.loads(row["val_json"]) if (row and row["val_json"] and row["val_json"] != "null") else None
                if not current and category in self._state:
                    current = self._state[category].get(key)

                curr_status = str(current.get("status", "")).upper() if isinstance(current, dict) else ""
                if curr_status and curr_status not in [s.upper() for s in expected_current]:
                    conn.commit()
                    return False

                merged_state = {**current, **(update_data or {}), "status": target_status} if isinstance(current, dict) else {"status": target_status, **(update_data or {})}
                val_json = json.dumps(merged_state)
                conn.execute("""
                INSERT INTO central_state (category, state_key, val_json, updated_at)
                VALUES (?, ?, ?, DATETIME('now'))
                ON CONFLICT(category, state_key) DO UPDATE SET
                    val_json=excluded.val_json,
                    updated_at=DATETIME('now')
                """, (category, key, val_json))
                conn.commit()

                if category not in self._state:
                    self._state[category] = {}
                self._state[category][key] = merged_state
                return True
            except Exception as ex:
                conn.rollback()
                raise ex

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {cat: dict(val) for cat, val in self._state.items()}
