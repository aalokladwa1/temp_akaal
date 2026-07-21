"""
Scenario 1 — End-to-End Happy Path Integration Test across Platforms 1, 2, and 3.
"""

from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.orchestration import EngineState
from akaal.distributed.domain.identifiers import TaskId
from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.operators.base import MapOperator, FilterOperator


def test_scenario_1_end_to_end_happy_path():
    engine = CrossPlatformIntegrationEngine()

    # 1. Register Platform 2 worker node
    worker = engine.register_worker_node("worker_node_1")
    assert worker.node_id.value == "node_worker_node_1"

    # 2. Platform 1 submits MigrationJob
    job = create_sample_migration_job("job_happy_path_1", "Oracle to PostgreSQL Migration")
    
    operators = [
        MapOperator(fn=lambda d: {"val": d["raw"] * 2}),
        FilterOperator(predicate=lambda d: d["val"] > 10),
    ]

    submitted = engine.submit_migration_job(job, streaming_operators=operators)
    assert submitted.current_state == EngineState.CREATED

    # Platform 2 Task Queue verification
    assert engine.distributed_runtime.queue.size() == 1

    # 3. Execute processing step through Platform 3
    records = [StreamRecord(payload={"raw": i}, event_time=float(i)) for i in range(10)]
    result = engine.execute_scheduled_step("job_happy_path_1", records)

    assert result["status"] == "SUCCESS"
    assert result["processed"] == 10
    assert result["output_count"] == 4  # raw > 5 => 6, 7, 8, 9

    # 4. Platform 1 Marks Job Completed
    completed = engine.complete_migration_job("job_happy_path_1")
    assert completed.current_state == EngineState.COMPLETED

    # 5. Resource Cleanup Verification
    assert "job_happy_path_1" not in engine.streaming_runtimes

    # 6. Audit Trail Verification
    audit_history = engine.get_audit_history("job_happy_path_1")
    assert len(audit_history) >= 3
    event_types = [e.details.get("to_state") for e in audit_history]
    assert "JOB_SUBMITTED" in event_types
    assert "TASK_ENQUEUED_P2" in event_types
    assert "JOB_COMPLETED" in event_types
