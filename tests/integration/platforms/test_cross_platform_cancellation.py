"""
Scenario 5 — Job Cancellation Integration Test across Platforms 1, 2, and 3.
"""

from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.orchestration import EngineState
from akaal.streaming.operators.base import MapOperator


def test_scenario_5_cancellation_propagation():
    engine = CrossPlatformIntegrationEngine()
    engine.register_worker_node("worker_cancel")

    job = create_sample_migration_job("job_cancel_1", "Long-Running Job To Cancel")
    engine.submit_migration_job(job, streaming_operators=[MapOperator(fn=lambda d: {"v": d["v"]})])

    assert "job_cancel_1" in engine.streaming_runtimes

    # Cancel job from Platform 1
    cancelled = engine.cancel_migration_job("job_cancel_1")
    assert cancelled.current_state == EngineState.CANCELLED

    # Platform 3 runtime terminated and cleaned up
    assert "job_cancel_1" not in engine.streaming_runtimes

    # Audit trail verifies cancellation
    history = engine.get_audit_history("job_cancel_1")
    event_types = [h.details.get("to_state") for h in history]
    assert "JOB_CANCELLED" in event_types
