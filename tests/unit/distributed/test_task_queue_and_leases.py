"""
Unit tests for TaskQueue and LeaseManager.
"""

import pytest

from akaal.distributed.domain.identifiers import TaskId, ExecutionId, WorkerId, LeaseId, IdempotencyKey, CorrelationId
from akaal.distributed.domain.models import Task, ExecutionRequest
from akaal.distributed.domain.errors import LeaseExpiredError
from akaal.distributed.queue.queue import MemoryTaskQueue
from akaal.distributed.worker.lease import LeaseManager
from akaal.distributed.repository.memory_repository import InMemoryLeaseRepository
from akaal.distributed.events.events import InProcessEventDispatcher
from akaal.distributed.clock.clock import TestClock


def test_memory_task_queue_priority_and_delayed():
    clock = TestClock(initial_timestamp=100.0)
    queue = MemoryTaskQueue(clock=clock)

    task_low = Task(task_id=TaskId("t_low"), execution_id=ExecutionId("e1"), name="low", priority=1)
    task_high = Task(task_id=TaskId("t_high"), execution_id=ExecutionId("e2"), name="high", priority=100)
    task_delayed = Task(task_id=TaskId("t_del"), execution_id=ExecutionId("e3"), name="delayed", priority=200, delay_seconds=20.0)

    req_low = ExecutionRequest(execution_id=task_low.execution_id, correlation_id=CorrelationId.generate(), task=task_low, idempotency_key=IdempotencyKey.generate())
    req_high = ExecutionRequest(execution_id=task_high.execution_id, correlation_id=CorrelationId.generate(), task=task_high, idempotency_key=IdempotencyKey.generate())
    req_del = ExecutionRequest(execution_id=task_delayed.execution_id, correlation_id=CorrelationId.generate(), task=task_delayed, idempotency_key=IdempotencyKey.generate())

    queue.enqueue(req_low)
    queue.enqueue(req_high)
    queue.enqueue(req_del)

    # Dequeue 1: high priority comes first
    d1 = queue.dequeue()
    assert d1.task.task_id == task_high.task_id

    # Dequeue 2: low priority comes next (delayed task not ready at t=100)
    d2 = queue.dequeue()
    assert d2.task.task_id == task_low.task_id

    # Dequeue 3: None ready
    assert queue.dequeue() is None

    # Advance clock by 25s
    clock.advance(25.0)

    # Dequeue 4: delayed task now ready
    d3 = queue.dequeue()
    assert d3.task.task_id == task_delayed.task_id


def test_lease_manager_expiration_and_time_warping():
    clock = TestClock(initial_timestamp=1000.0)
    repo = InMemoryLeaseRepository()
    dispatcher = InProcessEventDispatcher()
    lease_mgr = LeaseManager(repository=repo, publisher=dispatcher, default_ttl_seconds=30.0, clock=clock)

    w_id = WorkerId("w1")
    t_id = TaskId("t1")

    lease = lease_mgr.acquire_lease(w_id, t_id)
    assert lease.expires_at == 1030.0

    # Renew lease at t=1010
    clock.advance(10.0)
    renewed = lease_mgr.renew_lease(lease.lease_id, w_id)
    assert renewed.expires_at == 1040.0

    # Advance clock past expiration (t=1050)
    clock.advance(40.0)

    # Renewing should fail
    with pytest.raises(LeaseExpiredError, match="expired"):
        lease_mgr.renew_lease(lease.lease_id, w_id)

    # Evict expired leases
    expired = lease_mgr.check_and_evict_expired_leases()
    assert len(expired) == 1
    assert expired[0].lease_id == lease.lease_id
