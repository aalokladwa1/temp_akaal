"""
Unit tests for shared domain types, MigrationJob model, and Event System.
"""

import pytest
from akaal.orchestration.domain.identifiers import JobId, WorkflowId, SessionId, ConfigurationId
from akaal.orchestration.domain.types import Version, Checksum, EngineState, WorkflowStepName, AuditMetadata
from akaal.orchestration.domain.errors import (
    WorkflowError,
    InvalidStateTransitionError,
    RecoveryError,
    ConfigurationError,
    SessionExpiredError,
    CheckpointError,
    RepositoryError,
    WorkflowExecutionError,
)
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.events.events import InProcessEventDispatcher, EventSubscriber, DomainEvent, WorkflowStarted


class FailingSubscriber(EventSubscriber):
    def on_event(self, event: DomainEvent) -> None:
        raise RuntimeError("Subscriber A simulated failure")


class SuccessfulSubscriber(EventSubscriber):
    def __init__(self) -> None:
        self.received_events = []

    def on_event(self, event: DomainEvent) -> None:
        self.received_events.append(event)


def test_identifiers_generation_and_validation():
    job_id = JobId.generate()
    assert str(job_id).startswith("job_")
    
    wf_id = WorkflowId.generate()
    assert str(wf_id).startswith("wf_")

    sess_id = SessionId.generate()
    assert str(sess_id).startswith("sess_")

    cfg_id = ConfigurationId.generate()
    assert str(cfg_id).startswith("cfg_")

    with pytest.raises(ValueError):
        JobId("")


def test_types_and_checksum():
    ver = Version(1)
    assert int(ver) == 1
    assert int(ver.increment()) == 2

    with pytest.raises(ValueError):
        Version(0)

    data = {"key": "value", "count": 42}
    checksum1 = Checksum.from_dict(data)
    checksum2 = Checksum.from_dict(data)
    assert checksum1.digest == checksum2.digest
    assert len(str(checksum1)) == 64

    with pytest.raises(ValueError):
        Checksum("invalid_checksum")


def test_migration_job_immutability_and_updates():
    j_id = JobId.generate()
    w_id = WorkflowId.generate()
    s_id = SessionId.generate()
    c_id = ConfigurationId.generate()

    job = MigrationJob(
        job_id=j_id,
        workflow_id=w_id,
        session_id=s_id,
        config_id=c_id,
        source_profile={"db": "oracle"},
        target_profile={"db": "postgres"},
    )

    assert job.current_state == EngineState.CREATED
    initial_checksum = job.checksum
    initial_version = int(job.version)

    # Immutable update
    updated_job = job.with_updates(current_state=EngineState.RUNNING, updated_by="test_user")

    assert job.current_state == EngineState.CREATED
    assert updated_job.current_state == EngineState.RUNNING
    assert int(updated_job.version) == initial_version + 1
    assert updated_job.checksum != initial_checksum
    assert updated_job.audit_metadata.updated_by == "test_user"


def test_exception_hierarchy():
    err = InvalidStateTransitionError("CREATED", "RUNNING", "Illegal leap")
    assert isinstance(err, WorkflowError)
    assert err.details["from_state"] == "CREATED"
    assert err.details["to_state"] == "RUNNING"


def test_event_dispatcher_failure_isolation():
    """
    Subscriber A throwing an exception must NOT prevent Subscriber B from receiving the event.
    """
    dispatcher = InProcessEventDispatcher()
    failing_sub = FailingSubscriber()
    successful_sub = SuccessfulSubscriber()

    # Register both subscribers
    dispatcher.subscribe(failing_sub)
    dispatcher.subscribe(successful_sub)

    event = WorkflowStarted(aggregate_id="wf_100", workflow_id="wf_100", job_id="job_100")
    
    # Publish event (should not throw despite failing_sub)
    dispatcher.publish(event)

    # Verify Subscriber B still received the event
    assert len(successful_sub.received_events) == 1
    assert successful_sub.received_events[0] == event
