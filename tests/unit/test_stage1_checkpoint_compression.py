"""
Unit tests for Stage 1: Smart Checkpoint Compression.
"""

import pytest
from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.types import EngineState


def test_workflow_checkpoint_uncompressed_backward_compatibility():
    chk = WorkflowCheckpoint(
        checkpoint_id="chk-001",
        workflow_id=WorkflowId("wf-100"),
        job_id=JobId("job-200"),
        step_name="extract_step",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-hash",
        state_data={"last_pk": 5000, "rows_processed": 50000},
    )

    d = chk.to_dict()
    assert d["compressed"] is False
    assert d["checkpoint_id"] == "chk-001"
    assert chk.verify_checksum() is True

    # Deserialize legacy dict
    restored = WorkflowCheckpoint.from_dict(d)
    assert restored.checkpoint_id == chk.checkpoint_id
    assert restored.state_data == chk.state_data
    assert restored.verify_checksum() is True


def test_workflow_checkpoint_compressed_codecs():
    large_state = {"records": [{"id": i, "name": f"user_{i}"} for i in range(1000)]}

    chk = WorkflowCheckpoint(
        checkpoint_id="chk-002",
        workflow_id=WorkflowId("wf-101"),
        job_id=JobId("job-201"),
        step_name="transform_step",
        step_index=2,
        engine_state=EngineState.COMPLETED,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-hash-2",
        state_data=large_state,
    )

    # Auto compression
    comp_auto = chk.serialize_compressed(codec="auto")
    assert comp_auto["compressed"] is True
    assert comp_auto["compression_codec"] in ("zstd", "gzip", "lz4")
    assert comp_auto["compressed_bytes"] < comp_auto["uncompressed_bytes"]

    # Deserialize & verify SHA-256
    restored = WorkflowCheckpoint.from_dict(comp_auto)
    assert restored.checkpoint_id == "chk-002"
    assert restored.state_data == large_state
    assert restored.verify_checksum() is True

    # Test explicit gzip codec
    comp_gzip = chk.serialize_compressed(codec="gzip")
    assert comp_gzip["compression_codec"] == "gzip"
    restored_gzip = WorkflowCheckpoint.from_dict(comp_gzip)
    assert restored_gzip.state_data == large_state
