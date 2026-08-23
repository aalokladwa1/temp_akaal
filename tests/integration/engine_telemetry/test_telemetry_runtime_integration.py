"""
tests/integration/engine_telemetry/test_telemetry_runtime_integration.py
==========================================================================
Integration tests for Authority #7 Telemetry physical integration with Authority #6 Runtime.
"""

import tempfile
import pytest
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
from akaalEngine.runtime import RuntimeAuthority, TaskSpec, WorkerSpec, WorkerCapability
from akaalEngine.telemetry import TelemetryAuthority, HealthState, OperationalEvent


@pytest.fixture
def temp_durability_authority():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = DurabilityConfig(
            storage_dir=tmp_dir,
            fencing_signing_key=b"fencing_secret_key_1234567890123",
            journal_anchor_key=b"journal_anchor_key_1234567890123",
        )
        dur = DurabilityAuthority(config)
        yield dur
        dur.close()


def test_telemetry_runtime_and_durability_integration(temp_durability_authority):
    """Proves TelemetryAuthority samples RuntimeAuthority snapshots and aggregates operational facts."""
    dur = temp_durability_authority
    runtime = RuntimeAuthority(durability_authority=dur)
    runtime.start()

    telemetry = TelemetryAuthority(runtime_authority=runtime)

    # Register worker on Runtime
    w_spec = WorkerSpec(worker_id="w_tel_1", node_id="n1", capabilities=(WorkerCapability(name="extract"),))
    runtime.register_worker(w_spec)

    # Update health and record event
    telemetry.update_component_health("runtime_engine", HealthState.HEALTHY, reason="Runtime active")
    telemetry.publish_event(OperationalEvent(name="worker_registered", attributes={"worker_id": "w_tel_1"}))

    # Sample aggregate runtime telemetry snapshot
    snap = telemetry.get_runtime_telemetry_snapshot()
    assert "runtime_snapshot" in snap
    assert snap["runtime_snapshot"]["is_running"] is True
    assert len(snap["runtime_snapshot"]["active_workers"]) == 1

    assert snap["health_snapshot"]["overall_state"] == "HEALTHY"
    assert len(telemetry.get_event_history()) == 1

    runtime.shutdown()
