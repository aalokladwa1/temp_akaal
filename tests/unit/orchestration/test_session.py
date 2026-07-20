"""
Unit tests for Session Management and SessionCoordinator.
"""

import pytest
import time
from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.errors import SessionExpiredError
from akaal.orchestration.session.session import WorkflowSession, SessionStatus
from akaal.orchestration.repository.memory_repository import InMemorySessionRepository
from akaal.orchestration.events.events import InProcessEventDispatcher
from akaal.orchestration.engine.session_coordinator import SessionCoordinator


def test_session_lifecycle_and_heartbeat():
    repo = InMemorySessionRepository()
    dispatcher = InProcessEventDispatcher()
    coordinator = SessionCoordinator(repo, dispatcher)

    w_id = WorkflowId.generate()
    j_id = JobId.generate()

    session = coordinator.create_session(
        workflow_id=w_id,
        job_id=j_id,
        lease_timeout_seconds=0.5,
        heartbeat_interval_seconds=0.1,
    )

    assert session.status == SessionStatus.ACTIVE
    assert repo.get_session(session.session_id) is not None

    # Resume token verification
    token = session.resume_token
    assert session.verify_resume_token(token) is True
    assert session.verify_resume_token("invalid_token") is False

    # Heartbeat update
    updated_session = coordinator.heartbeat(session.session_id)
    assert updated_session.last_heartbeat >= session.last_heartbeat

    # Graceful closure
    closed = coordinator.close_session(session.session_id)
    assert closed.status == SessionStatus.CLOSED


def test_session_crash_detection_and_expiration():
    repo = InMemorySessionRepository()
    dispatcher = InProcessEventDispatcher()
    coordinator = SessionCoordinator(repo, dispatcher)

    w_id = WorkflowId.generate()
    j_id = JobId.generate()

    session = coordinator.create_session(
        workflow_id=w_id,
        job_id=j_id,
        lease_timeout_seconds=0.1,  # Fast timeout for test
    )

    # Wait for lease timeout
    time.sleep(0.15)

    # Heartbeat on expired session should raise SessionExpiredError
    with pytest.raises(SessionExpiredError):
        coordinator.heartbeat(session.session_id)

    # Crash detection should mark session as CRASHED
    crashed = coordinator.detect_and_handle_crash(session.session_id)
    assert crashed is True

    stored = repo.get_session(session.session_id)
    assert stored.status == SessionStatus.CRASHED
