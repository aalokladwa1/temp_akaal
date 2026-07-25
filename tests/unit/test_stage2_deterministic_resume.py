"""
Unit tests for Stage 2: Deterministic Resume Engine.
"""

import pytest
from akaal.migration.execution.resume_engine import DeterministicResumeEngine
from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.types import EngineState


def test_deterministic_resume_pk_spec():
    chk = WorkflowCheckpoint(
        checkpoint_id="chk-100",
        workflow_id=WorkflowId("wf-1"),
        job_id=JobId("j-1"),
        step_name="step_extract",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-1",
        state_data={"last_committed_batch": 42, "last_seen_pk": 9500},
    )

    engine = DeterministicResumeEngine()
    spec = engine.build_resume_spec(
        table_name="orders",
        checkpoint=chk,
        pk_columns=["order_id"],
    )

    assert spec.resume_mode == "PRIMARY_KEY"
    assert spec.where_clause == "orders.order_id > :last_seen_pk"
    assert spec.bind_params["last_seen_pk"] == 9500
    assert spec.last_committed_batch == 42


def test_deterministic_resume_prohibits_offset():
    chk = WorkflowCheckpoint(
        checkpoint_id="chk-101",
        workflow_id=WorkflowId("wf-1"),
        job_id=JobId("j-1"),
        step_name="step_extract",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-1",
        state_data={"last_committed_batch": 10},
    )

    engine = DeterministicResumeEngine()
    with pytest.raises(ValueError, match="strictly prohibits OFFSET-based recovery"):
        engine.build_resume_spec(
            table_name="customers",
            checkpoint=chk,
            allow_offset=True,
        )


def test_deterministic_resume_rowid_spec():
    chk = WorkflowCheckpoint(
        checkpoint_id="chk-102",
        workflow_id=WorkflowId("wf-1"),
        job_id=JobId("j-1"),
        step_name="step_extract",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-1",
        state_data={"last_committed_batch": 5, "last_seen_rowid": "AAABBBCCC"},
    )

    engine = DeterministicResumeEngine()
    spec = engine.build_resume_spec(
        table_name="large_table",
        checkpoint=chk,
        use_rowid=True,
    )

    assert spec.resume_mode == "ROWID"
    assert spec.where_clause == "large_table.ROWID > :last_seen_rowid"
    assert spec.bind_params["last_seen_rowid"] == "AAABBBCCC"
