"""
Unit tests for ClusterScheduler and pluggable scheduling policies.
"""

from akaal.distributed.domain.identifiers import WorkerId, NodeId, TaskId, ExecutionId
from akaal.distributed.domain.models import Worker, Task, ResourceSnapshot
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth
from akaal.distributed.scheduler.policy import (
    FIFOSchedulingPolicy,
    PrioritySchedulingPolicy,
    LeastLoadedSchedulingPolicy,
    ResourceAwareSchedulingPolicy,
    AffinitySchedulingPolicy,
    AntiAffinitySchedulingPolicy,
    LocalityAwareSchedulingPolicy,
)


def test_scheduling_policies():
    w1 = Worker(
        worker_id=WorkerId("w1"),
        node_id=NodeId("node_a"),
        status=WorkerStatus.AVAILABLE,
        health=WorkerHealth.HEALTHY,
        capacity=10,
        current_load=8,
        resources=ResourceSnapshot(cpu_cores=2.0, memory_mb=2048.0),
        labels={"zone": "us-east"},
    )
    w2 = Worker(
        worker_id=WorkerId("w2"),
        node_id=NodeId("node_b"),
        status=WorkerStatus.AVAILABLE,
        health=WorkerHealth.HEALTHY,
        capacity=10,
        current_load=2,
        resources=ResourceSnapshot(cpu_cores=8.0, memory_mb=8192.0),
        labels={"zone": "us-west"},
    )
    candidates = [w1, w2]
    task = Task(task_id=TaskId("t1"), execution_id=ExecutionId("e1"), name="task1", labels={"zone": "us-west"})

    # 1. FIFO
    assert FIFOSchedulingPolicy().select_worker(task, candidates) == w1

    # 2. LeastLoaded
    assert LeastLoadedSchedulingPolicy().select_worker(task, candidates) == w2

    # 3. ResourceAware
    assert ResourceAwareSchedulingPolicy().select_worker(task, candidates) == w2

    # 4. Affinity
    assert AffinitySchedulingPolicy().select_worker(task, candidates) == w2

    # 5. LocalityAware
    task_loc = Task(task_id=TaskId("t2"), execution_id=ExecutionId("e2"), name="task2", payload={"preferred_node_id": "node_a"})
    assert LocalityAwareSchedulingPolicy().select_worker(task_loc, candidates) == w1
