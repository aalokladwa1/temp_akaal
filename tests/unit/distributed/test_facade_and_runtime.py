"""
Unit tests for DistributedRuntimeV1 public facade and idempotent task submission.
"""

from akaal.distributed.facade.runtime import DefaultDistributedRuntimeV1
from akaal.distributed.domain.identifiers import NodeId, TaskId, ExecutionId, IdempotencyKey
from akaal.distributed.domain.models import Task
from akaal.distributed.clock.clock import TestClock


def test_distributed_runtime_facade_and_idempotency():
    clock = TestClock(initial_timestamp=100.0)
    runtime = DefaultDistributedRuntimeV1(clock=clock)

    # Register worker
    primary_node = NodeId("node_primary")
    worker = runtime.register_worker(primary_node, capacity=5)
    assert worker.status.value == "AVAILABLE"

    # Submit task with IdempotencyKey
    task = Task(
        task_id=TaskId("task_001"),
        execution_id=ExecutionId("exec_001"),
        name="DDL_MIGRATION_STEP",
    )
    key = IdempotencyKey("idempotent_key_abc")

    req1 = runtime.submit_task(task, idempotency_key=key)
    assert req1.task.task_id == task.task_id

    # Duplicate submission returns exact same request (deduplicated)
    req2 = runtime.submit_task(task, idempotency_key=key)
    assert req1 == req2

    # Process next task via facade
    res = runtime.process_next()
    assert res is not None
    assert res.execution_id == task.execution_id
    assert res.status == "SUCCESS"

    # Health check verification
    health = runtime.get_cluster_health()
    assert health["status"] == "HEALTHY"
    assert health["total_workers"] >= 1


def test_scaling_and_worker_draining():
    clock = TestClock(initial_timestamp=200.0)
    runtime = DefaultDistributedRuntimeV1(clock=clock)
    node = NodeId("node_primary")

    scaled_workers = runtime.scale_up(node, count=2)
    assert len(scaled_workers) == 2

    drained = runtime.drain_worker(scaled_workers[0].worker_id)
    assert drained.status.value == "DRAINING"
