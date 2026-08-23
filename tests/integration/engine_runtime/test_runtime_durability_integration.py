"""
tests/integration/engine_runtime/test_runtime_durability_integration.py
========================================================================
Integration test proving physical integration between Authority #6 Runtime
and Authority #5 Durability (Fencing tokens, Lease persistence, and Recovery State Inspection).
"""

import tempfile
import pytest
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
from akaalEngine.runtime import RuntimeAuthority, TaskSpec, WorkerSpec, WorkerCapability


@pytest.fixture
def temp_durability_authority():
    """Provides an active DurabilityAuthority for integration testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = DurabilityConfig(
            storage_dir=tmp_dir,
            fencing_signing_key=b"fencing_secret_key_1234567890123",
            journal_anchor_key=b"journal_anchor_key_1234567890123",
        )
        dur = DurabilityAuthority(config)
        yield dur
        dur.close()


def test_runtime_durability_fencing_and_recovery_integration(temp_durability_authority):
    """Proves RuntimeAuthority physically issues durable fencing tokens and evaluates recovery snapshots."""
    dur = temp_durability_authority
    runtime = RuntimeAuthority(durability_authority=dur)
    runtime.start()

    # Issue durable fencing token via lease_manager
    lease = runtime.acquire_execution_lease(task_id="t_dur_1", worker_id="w_dur_1")
    assert lease.durability_token is not None
    assert lease.durability_token.resource_id == "t_dur_1"
    assert lease.durability_token.worker_id == "w_dur_1"
    assert lease.fencing_epoch == 1

    # Validate durable token
    assert dur.validate_fencing_token(lease.durability_token) is True

    # Test recovery state evaluation
    plan = runtime.recover_runtime_state("mig_test_1")
    assert plan.migration_id == "mig_test_1"
    assert plan.fencing_epoch >= 1

    runtime.shutdown()
