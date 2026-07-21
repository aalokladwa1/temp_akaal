"""
Scenario 4 — Platform 3 Failure Detection & Retry Policy Integration Test.
"""

import pytest
from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.streaming.domain.models import StreamRecord
from akaal.streaming.operators.base import MapOperator


class FaultyStreamOperator(MapOperator):
    def process_element(self, record: StreamRecord):
        if record.payload.get("fail"):
            raise RuntimeError("Stream operator failure injected!")
        return super().process_element(record)


def test_scenario_4_failure_detection_and_retry():
    engine = CrossPlatformIntegrationEngine()
    engine.register_worker_node("worker_fail_1")

    job = create_sample_migration_job("job_fail_1", "Failure Injection Job")

    op_faulty = FaultyStreamOperator(fn=lambda d: {"v": d["v"]})
    engine.submit_migration_job(job, streaming_operators=[op_faulty])

    # Push failing record -> raises exception
    bad_records = [StreamRecord(payload={"v": 1, "fail": True}, event_time=1.0)]
    with pytest.raises(RuntimeError, match="Stream operator failure injected!"):
        engine.execute_scheduled_step("job_fail_1", bad_records)

    # Retry step with valid record succeeds cleanly
    good_records = [StreamRecord(payload={"v": 10}, event_time=2.0)]
    res = engine.execute_scheduled_step("job_fail_1", good_records)
    assert res["status"] == "SUCCESS"
    assert res["processed"] == 1
