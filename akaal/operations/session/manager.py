"""
Operations Session Manager.
Tracks operator activities within immutable operational sessions.
"""

from typing import Dict, List, Any, Optional
from threading import RLock
from enum import Enum
import time


class SessionState(Enum):
    CREATED = "Created"
    ACTIVE = "Active"
    VERIFYING = "Verifying"
    CLOSED = "Closed"
    ABORTED = "Aborted"


class OperationsSession:
    """An immutable administrative activity session."""

    def __init__(self, session_id: str, operator_id: str, session_type: str = "Maintenance") -> None:
        self._lock = RLock()
        self.session_id = session_id
        self.operator_id = operator_id
        self.session_type = session_type
        self.state = SessionState.CREATED
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.executed_actions: List[Dict[str, Any]] = []
        self.policy_decisions: List[Dict[str, Any]] = []
        self.approvals: List[str] = []
        self.outcome = "PENDING"

    def record_action(self, action_name: str, target_platform: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if self.state == SessionState.CLOSED:
                raise RuntimeError(f"Session '{self.session_id}' is closed and immutable.")
            self.executed_actions.append({
                "timestamp": time.time(),
                "action": action_name,
                "target_platform": target_platform,
                "status": status,
                "details": details or {}
            })

    def close(self, outcome: str = "SUCCESS") -> None:
        with self._lock:
            self.state = SessionState.CLOSED
            self.end_time = time.time()
            self.outcome = outcome


class OperationsSessionManager:
    """Manages active and historical operational sessions."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Dict[str, OperationsSession] = {}

    def start_session(self, operator_id: str, session_type: str = "Maintenance") -> OperationsSession:
        with self._lock:
            sid = f"ops_sess_{time.time_ns()}_{len(self._sessions)}"
            session = OperationsSession(sid, operator_id, session_type)
            session.state = SessionState.ACTIVE
            self._sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> Optional[OperationsSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def close_session(self, session_id: str, outcome: str = "SUCCESS") -> Optional[OperationsSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.close(outcome)
            return session
