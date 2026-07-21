"""
Scenario 2 & Scenario 7 — Multiple Concurrent Jobs & High Load Stress Integration Test.
"""

import concurrent.futures
from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.orchestration import EngineState
from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.operators.base import MapOperator


def test_scenario_2_and_7_concurrent_jobs_and_high_load():
    engine = CrossPlatformIntegrationEngine()
    engine.register_worker_node("worker_stress_1")
    engine.register_worker_node("worker_stress_2")

    job_count = 10
    records_per_job = 200

    # 1. Submit 10 concurrent migration jobs
    def run_job(job_idx: int):
        job_id = f"concurrent_job_{job_idx}"
        job = create_sample_migration_job(job_id, f"Migration Job {job_idx}")
        engine.submit_migration_job(
            job,
            streaming_operators=[MapOperator(fn=lambda d: {"job": job_idx, "v": d["v"] * 2})],
        )

        records = [StreamRecord(payload={"v": i}, event_time=float(i)) for i in range(records_per_job)]
        res = engine.execute_scheduled_step(job_id, records)
        completed = engine.complete_migration_job(job_id)
        return completed.current_state

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_job, i) for i in range(job_count)]
        statuses = [f.result() for f in futures]

    assert len(statuses) == job_count
    assert all(s == EngineState.COMPLETED for s in statuses)

    # Clean resource state verification
    assert len(engine.streaming_runtimes) == 0
