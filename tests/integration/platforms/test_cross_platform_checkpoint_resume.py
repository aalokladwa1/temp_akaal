"""
Scenario 6 — Checkpoint & Resume Integration Test across Platforms 1, 2, and 3.
"""

from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.orchestration import WorkflowCheckpoint, JobId, EngineState
from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.operators.base import MapOperator


def test_scenario_6_checkpoint_and_resume():
    engine = CrossPlatformIntegrationEngine()
    engine.register_worker_node("worker_ckpt")

    job = create_sample_migration_job("job_ckpt_1", "Checkpoint Resume Job")
    engine.submit_migration_job(job, streaming_operators=[MapOperator(fn=lambda d: {"v": d["v"] * 2})])

    # 1. Process initial batch of records (1-5)
    recs1 = [StreamRecord(payload={"v": i}, event_time=float(i)) for i in range(1, 6)]
    res1 = engine.execute_scheduled_step("job_ckpt_1", recs1)
    assert res1["processed"] == 5

    # 2. Create Platform 1 Checkpoint at sequence position 5
    ckpt = WorkflowCheckpoint(
        checkpoint_id="ckpt_job_ckpt_1",
        workflow_id=job.workflow_id,
        job_id=job.job_id,
        step_name="step_stream_processing",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="abc",
        state_data={"last_processed_seq": 5, "checkpoint_timestamp": 5.0},
    )
    engine.workflow_engine.checkpoint_repo.save_checkpoint(ckpt)

    # 3. Simulate stream interruption & restart (re-initialize Streaming Runtime for job)
    stream_rt = engine.streaming_runtimes["job_ckpt_1"]
    stream_rt.engine._input_queue.clear()

    # 4. Resume processing from checkpoint position (6-10)
    restored_ckpt = engine.workflow_engine.checkpoint_repo.get_latest_checkpoint(job.workflow_id)
    assert restored_ckpt.state_data["last_processed_seq"] == 5

    recs2 = [StreamRecord(payload={"v": i}, event_time=float(i)) for i in range(6, 11)]
    res2 = engine.execute_scheduled_step("job_ckpt_1", recs2)
    assert res2["processed"] == 5
    assert res2["outputs"][0].payload["v"] == 12  # 6 * 2
    assert res2["outputs"][4].payload["v"] == 20  # 10 * 2
