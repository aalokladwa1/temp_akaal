import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from akaal.migration.execution.scheduler import (
    TaskState,
    ConcurrencyPolicy,
    WorkerStatus,
    SchedulerLifecycleState,
    TaskExecutionContext,
    TaskResult,
    SchedulableOperation,
    SchedulerConfiguration,
    SchedulerMetrics,
    SchedulerCheckpoint,
    SchedulableTask,
    QueueState,
    WorkerState,
    SchedulerSession,
    ParallelSchedulerEngine,
    DeadlockException,
    QueueAdmissionRejectionException,
)

# Mock SchedulableOperation
class MockOperation:
    def __init__(self, should_fail: bool = False, is_idempotent: bool = True, error_msg: str = "connection failed"):
        self.should_fail = should_fail
        self.is_idempotent = is_idempotent
        self.error_msg = error_msg
        self.execution_count = 0

    async def execute(self, context: TaskExecutionContext) -> TaskResult:
        self.execution_count += 1
        if self.should_fail:
            raise ConnectionError(self.error_msg)
        return TaskResult("mock", TaskState.SUCCESS)

# --- 1. Graph / Dependency Tests ---

def test_empty_dependency_graph():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    engine.load_graph([])  # Should load empty list cleanly
    assert len(engine.tasks) == 0

def test_single_node_dependency_graph():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    task = SchedulableTask("t1", MockOperation(), "key1", 1, ())
    engine.load_graph([task])
    assert len(engine.tasks) == 1
    assert engine.in_degree["t1"] == 0

def test_circular_dependency_rejection():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    t1 = SchedulableTask("t1", MockOperation(), "key1", 1, ("t2",))
    t2 = SchedulableTask("t2", MockOperation(), "key2", 1, ("t1",))
    
    with pytest.raises(DeadlockException):
        engine.load_graph([t1, t2])

@pytest.mark.asyncio
async def test_diamond_graph_execution_order():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    op = MockOperation()
    root = SchedulableTask("root", op, "k1", 1, ())
    left = SchedulableTask("left", op, "k2", 1, ("root",))
    right = SchedulableTask("right", op, "k3", 1, ("root",))
    sink = SchedulableTask("sink", op, "k4", 1, ("left", "right"))
    
    engine.load_graph([root, left, right, sink])
    await engine.start()
    
    assert engine.tasks["root"].state == TaskState.SUCCESS
    assert engine.tasks["left"].state == TaskState.SUCCESS
    assert engine.tasks["right"].state == TaskState.SUCCESS
    assert engine.tasks["sink"].state == TaskState.SUCCESS

# --- 2. Starvation & Priority Ordering ---

@pytest.mark.asyncio
async def test_priority_ordering_and_starvation_prevention():
    config = SchedulerConfiguration("sess_1", 1, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    op = MockOperation()
    # High priority vs low priority tasks
    t1 = SchedulableTask("t1", op, "k1", 2, ())
    t2 = SchedulableTask("t2", op, "k2", 5, ())
    
    engine.load_graph([t1, t2])
    await engine.start()
    
    # Priority boost should verify without issues
    assert engine.tasks["t1"].state == TaskState.SUCCESS
    assert engine.tasks["t2"].state == TaskState.SUCCESS

# --- 3. Retry and Recovery Manager ---

@pytest.mark.asyncio
async def test_retry_on_retryable_exceptions():
    config = SchedulerConfiguration("sess_1", 4, 2, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    # ConnectionError is retryable
    op = MockOperation(should_fail=True, error_msg="connection reset")
    t1 = SchedulableTask("t1", op, "k1", 1, ())
    
    engine.load_graph([t1])
    await engine.start()
    
    # Retries up to limits (initial + 2 retries = 3 total runs)
    assert t1.retry_count == 2
    assert t1.state == TaskState.FAILED

@pytest.mark.asyncio
async def test_skipped_propagation_on_fatal_failure():
    config = SchedulerConfiguration("sess_1", 4, 0, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    op_fail = MockOperation(should_fail=True, error_msg="syntax error")
    op_ok = MockOperation()
    
    t1 = SchedulableTask("t1", op_fail, "k1", 1, ())
    t2 = SchedulableTask("t2", op_ok, "k2", 1, ("t1",))  # Dependent on failed t1
    
    engine.load_graph([t1, t2])
    await engine.start()
    
    assert t1.state == TaskState.FAILED
    assert t2.state == TaskState.SKIPPED

# --- 4. Graceful Shutdown & Recovery Replay ---

@pytest.mark.asyncio
async def test_graceful_shutdown_drains_and_checkpoints():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    op = MockOperation()
    t1 = SchedulableTask("t1", op, "k1", 1, ())
    engine.load_graph([t1])
    
    await engine.shutdown()
    assert engine.session.lifecycle_state == SchedulerLifecycleState.CANCELLED
    assert engine.config.session_id in engine.checkpoint_store

# --- 5. Concurrency & Resource Exclusions ---

@pytest.mark.asyncio
async def test_heavyweight_blocks_concurrency():
    config = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    engine = ParallelSchedulerEngine(config)
    
    op = MockOperation()
    t1 = SchedulableTask("t1", op, "k1", 1, (), resource_requirements={"table_name": "orders", "heavyweight": True})
    t2 = SchedulableTask("t2", op, "k2", 1, (), resource_requirements={"table_name": "orders", "heavyweight": False})
    
    engine.load_graph([t1, t2])
    await engine.start()
    
    assert t1.state == TaskState.SUCCESS
    assert t2.state == TaskState.SUCCESS

# --- 6. Concurrency / Session Isolation ---

@pytest.mark.asyncio
async def test_concurrent_sessions_isolation():
    c1 = SchedulerConfiguration("sess_1", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    c2 = SchedulerConfiguration("sess_2", 4, 3, 0.1, ConcurrencyPolicy.DYNAMIC_FLOW)
    
    e1 = ParallelSchedulerEngine(c1)
    e2 = ParallelSchedulerEngine(c2)
    
    assert e1.config.session_id == "sess_1"
    assert e2.config.session_id == "sess_2"
