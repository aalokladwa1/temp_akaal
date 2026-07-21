"""
Unit tests for Clock abstraction and Domain Invariant Validations.
"""

import pytest

from akaal.distributed.clock.clock import SystemClock, TestClock
from akaal.distributed.domain.identifiers import (
    WorkerId, NodeId, ClusterId, TaskId, ExecutionId, AttemptId, LeaseId, CorrelationId, ReservationId, IdempotencyKey
)
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth, ClusterState, AssignmentState
from akaal.distributed.domain.errors import DomainValidationError
from akaal.distributed.domain.models import (
    Worker, Node, Lease, ExecutionToken, ResourceReservation, ClusterSnapshot, ClusterMembership, Task
)


def test_clock_abstraction_and_time_warping():
    sys_clock = SystemClock()
    assert sys_clock.now_timestamp() > 0
    assert sys_clock.monotonic() > 0

    test_clock = TestClock(initial_timestamp=1000.0)
    assert test_clock.now_timestamp() == 1000.0
    assert test_clock.monotonic() == 0.0

    test_clock.advance(50.0)
    assert test_clock.now_timestamp() == 1050.0
    assert test_clock.monotonic() == 50.0

    with pytest.raises(ValueError, match="Cannot advance test clock backwards"):
        test_clock.advance(-10.0)


def test_identifiers_generation():
    w_id = WorkerId.generate()
    n_id = NodeId.generate()
    c_id = ClusterId.generate()
    t_id = TaskId.generate()
    e_id = ExecutionId.generate()
    a_id = AttemptId.generate()
    l_id = LeaseId.generate()
    r_id = ReservationId.generate()
    i_key = IdempotencyKey.generate()

    assert str(w_id).startswith("worker_")
    assert str(n_id).startswith("node_")
    assert str(c_id).startswith("cluster_")
    assert str(t_id).startswith("task_")
    assert str(e_id).startswith("exec_")
    assert str(a_id).startswith("att_")
    assert str(l_id).startswith("lease_")
    assert str(r_id).startswith("resv_")
    assert str(i_key).startswith("idempotency_")


def test_domain_model_invariant_validations():
    w_id = WorkerId("w1")
    n_id = NodeId("n1")

    # Worker capacity must be non-negative
    with pytest.raises(DomainValidationError, match="Worker capacity must be non-negative"):
        Worker(worker_id=w_id, node_id=n_id, capacity=-1)

    # Lease expiration must be after creation
    with pytest.raises(DomainValidationError, match="Lease expiration must be strictly after creation timestamp"):
        Lease(
            lease_id=LeaseId("l1"),
            owner_worker_id=w_id,
            task_id=TaskId("t1"),
            created_at=100.0,
            expires_at=50.0,
        )

    # ResourceReservation amounts must be non-negative
    with pytest.raises(DomainValidationError, match="ResourceReservation resource amounts must be non-negative"):
        ResourceReservation(
            reservation_id=ReservationId("r1"),
            worker_id=w_id,
            cpu_cores=-2.0,
            memory_mb=1024.0,
            concurrency=1,
            created_at=10.0,
            expires_at=20.0,
        )
