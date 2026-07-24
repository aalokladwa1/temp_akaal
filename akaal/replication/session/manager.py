"""Replication Session Management: Checkpoints, Leases, Coordinator, and SessionManager."""

import time
import threading
import uuid
from typing import Dict, Any, Optional, List, Tuple
from akaal.replication.core.session import ReplicationSession
from akaal.replication.core.models import ReplicationStatus


class SessionCheckpointManager:
    """Persists and restores checkpoints for long-running replication sessions."""

    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def save_checkpoint(self, session_id: str, checkpoint_data: Dict[str, Any]) -> None:
        with self._lock:
            self._checkpoints[session_id] = {
                "timestamp": time.time(),
                "session_id": session_id,
                "data": checkpoint_data,
            }

    def get_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._checkpoints.get(session_id)


class SessionLeaseManager:
    """Manages distributed lease ownership and renewals for active sessions."""

    def __init__(self, default_ttl_sec: int = 30):
        self.default_ttl = default_ttl_sec
        self._leases: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, session_id: str, owner_id: str, ttl_sec: Optional[int] = None) -> bool:
        ttl = ttl_sec or self.default_ttl
        now = time.time()
        with self._lock:
            if session_id in self._leases:
                curr_owner, exp = self._leases[session_id]
                if curr_owner != owner_id and now < exp:
                    return False
            self._leases[session_id] = (owner_id, now + ttl)
            return True

    def renew_lease(self, session_id: str, owner_id: str, ttl_sec: Optional[int] = None) -> bool:
        return self.acquire_lease(session_id, owner_id, ttl_sec)

    def release_lease(self, session_id: str, owner_id: str) -> None:
        with self._lock:
            if session_id in self._leases and self._leases[session_id][0] == owner_id:
                del self._leases[session_id]


class SessionCoordinator:
    """Coordinates lifecycle transitions (Pause, Resume, Failover) across session nodes."""

    def pause_session(self, session: ReplicationSession) -> None:
        session.state = ReplicationStatus.PAUSED

    def resume_session(self, session: ReplicationSession) -> None:
        session.state = ReplicationStatus.IN_PROGRESS


class ReplicationSessionManager:
    """Master Session Manager tracking active long-running replication sessions."""

    def __init__(self):
        self.checkpoint_mgr = SessionCheckpointManager()
        self.lease_mgr = SessionLeaseManager()
        self.coordinator = SessionCoordinator()
        self._sessions: Dict[str, ReplicationSession] = {}
        self._lock = threading.RLock()

    def create_session(self, session_id: Optional[str] = None) -> ReplicationSession:
        sess = ReplicationSession(session_id)
        with self._lock:
            self._sessions[sess.session_id] = sess
        return sess

    def get_session(self, session_id: str) -> Optional[ReplicationSession]:
        with self._lock:
            return self._sessions.get(session_id)
