"""
SessionCoordinator module.
Coordinates session lifecycle, heartbeats, lease timeouts, locks, resume tokens, and crash detection.
"""

from typing import Optional
from datetime import datetime, timezone
import logging

from akaal.orchestration.session.session import WorkflowSession, SessionStatus
from akaal.orchestration.domain.identifiers import SessionId, WorkflowId, JobId
from akaal.orchestration.domain.errors import SessionExpiredError
from akaal.orchestration.repository.interfaces import SessionRepository
from akaal.orchestration.events.events import EventPublisher

logger = logging.getLogger("nexusforge.orchestration.session_coordinator")


class SessionCoordinator:
    """
    Manages session lifecycle and crash detection for distributed readiness.
    """

    def __init__(self, repository: SessionRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    def create_session(
        self,
        workflow_id: WorkflowId,
        job_id: JobId,
        node_id: str = "node_1",
        worker_id: str = "worker_1",
        lease_timeout_seconds: float = 30.0,
        heartbeat_interval_seconds: float = 5.0,
    ) -> WorkflowSession:
        """Create and persist a new active workflow session."""
        session = WorkflowSession(
            session_id=SessionId.generate(),
            workflow_id=workflow_id,
            job_id=job_id,
            owner_node_id=node_id,
            owner_worker_id=worker_id,
            lease_timeout_seconds=lease_timeout_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self._repository.save_session(session)
        return session

    def heartbeat(self, session_id: SessionId) -> WorkflowSession:
        """Update heartbeat timestamp for a session."""
        session = self._repository.get_session(session_id)
        if session is None:
            raise SessionExpiredError(f"Session '{session_id}' not found.")
        
        if session.is_expired():
            expired_session = session.with_status(SessionStatus.EXPIRED)
            self._repository.update_session(expired_session)
            raise SessionExpiredError(f"Session '{session_id}' lease expired.")

        updated = session.with_heartbeat()
        self._repository.update_session(updated)
        return updated

    def detect_and_handle_crash(self, session_id: SessionId) -> bool:
        """
        Detects if a session has crashed (lease expired without graceful closure).
        If crashed, updates session status to CRASHED.
        """
        session = self._repository.get_session(session_id)
        if session is None:
            return False
        
        if session.status in (SessionStatus.CLOSED, SessionStatus.CRASHED):
            return session.status == SessionStatus.CRASHED

        if session.is_expired():
            crashed = session.with_status(SessionStatus.CRASHED)
            self._repository.update_session(crashed)
            logger.warning(f"Session '{session_id}' detected as CRASHED due to lease timeout.")
            return True
        return False

    def close_session(self, session_id: SessionId) -> WorkflowSession:
        """Gracefully close a session."""
        session = self._repository.get_session(session_id)
        if session is None:
            raise SessionExpiredError(f"Session '{session_id}' not found.")
        closed = session.with_status(SessionStatus.CLOSED)
        self._repository.update_session(closed)
        return closed
