"""Unit tests for Checkpoint Storage Adapters (Memory and File) & Recovery."""

import pytest
import tempfile
from pathlib import Path
from akaal.workflow.checkpoint import CheckpointManager, FileBasedCheckpointStorage, InMemoryCheckpointStorage
from akaal.workflow.models import ExecutionContext, WorkflowContext
from akaal.workflow.utils import FixedClock, DeterministicIdGenerator


def test_in_memory_checkpoint_storage():
    clock = FixedClock()
    id_gen = DeterministicIdGenerator()
    manager = CheckpointManager(storage=InMemoryCheckpointStorage(), clock=clock, id_generator=id_gen)

    ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-1", run_id="run-1"))
    cp = manager.create_checkpoint(ctx, step_id="step-1", state="RUNNING", completed_steps=("step-1",))

    assert cp.checkpoint_id != ""
    assert cp.step_id == "step-1"

    loaded = manager.get_latest_checkpoint("wf-1", "run-1")
    assert loaded is not None
    assert loaded.checkpoint_id == cp.checkpoint_id
    assert loaded.completed_steps == ("step-1",)


def test_file_based_checkpoint_storage():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = FileBasedCheckpointStorage(tmp_dir)
        clock = FixedClock()
        id_gen = DeterministicIdGenerator()
        manager = CheckpointManager(storage=storage, clock=clock, id_generator=id_gen)

        ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-file-1", run_id="run-f1"))
        cp = manager.create_checkpoint(ctx, step_id="step-f1", state="PAUSED", completed_steps=("step-f1",))

        # Verify file creation
        file_path = Path(tmp_dir) / f"{cp.checkpoint_id}.json"
        assert file_path.exists()

        loaded = manager.get_checkpoint_by_id(cp.checkpoint_id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-file-1"
        assert loaded.state == "PAUSED"
