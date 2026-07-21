"""
Scenario 3 — Backpressure Propagation Integration Test across Platforms 1, 2, and 3.
"""

from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.domain.enums import BackpressureState
from akaal.streaming.operators.base import MapOperator


def test_scenario_3_backpressure_propagation():
    engine = CrossPlatformIntegrationEngine()
    engine.register_worker_node("worker_bp")

    job = create_sample_migration_job("job_bp_1", "Backpressure Test Job")
    engine.submit_migration_job(job, streaming_operators=[MapOperator(fn=lambda d: {"v": d["v"]})])

    stream_rt = engine.streaming_runtimes["job_bp_1"]
    
    # 1. Artificially set Platform 3 backpressure controller state to THROTTLED
    stream_rt.engine.backpressure_controller._state = BackpressureState.THROTTLED

    # 2. Attempt to execute step
    records = [StreamRecord(payload={"v": 1}, event_time=1.0)]
    res = engine.execute_scheduled_step("job_bp_1", records)

    # Verify Platform 2 scheduler throttled execution
    assert res["status"] == "THROTTLED"
    assert res["processed"] == 0

    # 3. Restore Platform 3 backpressure controller to NORMAL
    stream_rt.engine.backpressure_controller._state = BackpressureState.NORMAL

    # 4. Processing resumes cleanly
    res2 = engine.execute_scheduled_step("job_bp_1", records)
    assert res2["status"] == "SUCCESS"
    assert res2["processed"] == 1
