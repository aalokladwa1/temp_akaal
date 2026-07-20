"""
Unit tests for storage-agnostic repository implementations.
"""

import pytest
from akaal.orchestration.domain.identifiers import JobId, WorkflowId, SessionId, ConfigurationId
from akaal.orchestration.domain.types import EngineState
from akaal.orchestration.domain.errors import RepositoryError
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.session.session import WorkflowSession
from akaal.orchestration.audit.audit_logger import AuditRecord
from akaal.orchestration.repository.memory_repository import (
    InMemoryWorkflowRepository,
    InMemorySessionRepository,
    InMemoryCheckpointRepository,
    InMemoryAuditRepository,
)


def test_in_memory_workflow_repository():
    repo = InMemoryWorkflowRepository()
    job = MigrationJob(
        job_id=JobId.generate(),
        workflow_id=WorkflowId.generate(),
        session_id=SessionId.generate(),
        config_id=ConfigurationId.generate(),
        source_profile={"db": "source"},
        target_profile={"db": "target"},
    )

    repo.save_job(job)
    assert repo.get_job(job.job_id) == job

    # Duplicate save raises error
    with pytest.raises(RepositoryError):
        repo.save_job(job)

    # Query jobs
    jobs = repo.query_jobs(EngineState.CREATED)
    assert len(jobs) == 1
    assert jobs[0].job_id == job.job_id

    # Update job
    updated = job.with_updates(current_state=EngineState.RUNNING)
    repo.update_job(updated)
    assert repo.get_job(job.job_id).current_state == EngineState.RUNNING

    # History & Variables
    repo.save_execution_history(job.workflow_id, {"step": "ANALYSIS", "status": "OK"})
    history = repo.get_execution_history(job.workflow_id)
    assert len(history) == 1
    assert history[0]["step"] == "ANALYSIS"

    repo.save_execution_variable(job.workflow_id, "var1", 100)
    assert repo.get_execution_variable(job.workflow_id, "var1") == 100

    # Delete job
    repo.delete_job(job.job_id)
    assert repo.get_job(job.job_id) is None


def test_in_memory_session_repository():
    repo = InMemorySessionRepository()
    session = WorkflowSession(
        session_id=SessionId.generate(),
        workflow_id=WorkflowId.generate(),
        job_id=JobId.generate(),
        owner_node_id="node_1",
        owner_worker_id="worker_1",
    )

    repo.save_session(session)
    assert repo.get_session(session.session_id) == session

    repo.delete_session(session.session_id)
    assert repo.get_session(session.session_id) is None


def test_in_memory_audit_repository():
    repo = InMemoryAuditRepository()
    rec = AuditRecord(
        entry_id=1,
        event_type="WorkflowStarted",
        aggregate_id="wf_123",
        timestamp="2026-07-20T00:00:00Z",
        details={"job": "job_123"},
    )

    repo.save_audit_record(rec)
    records = repo.query_audit_records("wf_123")
    assert len(records) == 1
    assert records[0].checksum == rec.checksum
