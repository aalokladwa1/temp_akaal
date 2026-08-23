"""
tests/unit/engine_runtime/test_task_and_worker_fsm.py
======================================================
Unit tests for TaskState (10 states) FSM, WorkerState FSM, WorkerRegistry, and TaskAssignmentEngine.
"""

import pytest
from akaalEngine.runtime import (
    InvalidTaskTransitionError,
    RuntimeAuthority,
    TaskSpec,
    TaskState,
    WorkerCapability,
    WorkerNotFoundError,
    WorkerSpec,
    WorkerState,
    validate_task_transition,
)
from akaalEngine.runtime.workers.assignment import TaskAssignmentEngine
from akaalEngine.runtime.workers.registry import WorkerRegistry


def test_task_state_valid_and_invalid_transitions():
    """Proves TaskState FSM enforces valid transitions and rejects invalid state mutations."""
    # Valid
    validate_task_transition("t1", TaskState.PENDING, TaskState.ADMITTED)
    validate_task_transition("t1", TaskState.ADMITTED, TaskState.ASSIGNED)
    validate_task_transition("t1", TaskState.ASSIGNED, TaskState.RUNNING)
    validate_task_transition("t1", TaskState.RUNNING, TaskState.SUCCEEDED)

    # Invalid: SUCCEEDED -> RUNNING
    with pytest.raises(InvalidTaskTransitionError) as exc_info:
        validate_task_transition("t1", TaskState.SUCCEEDED, TaskState.RUNNING)
    assert exc_info.value.details["current_state"] == "SUCCEEDED"
    assert exc_info.value.details["target_state"] == "RUNNING"


def test_worker_registration_and_snapshot_lifecycle():
    """Proves WorkerRegistry manages worker registration, slot availability, and deregistration."""
    reg = WorkerRegistry()
    spec = WorkerSpec(
        worker_id="w1",
        node_id="n1",
        capabilities=(WorkerCapability(name="bulk_extract"),),
        max_concurrency_slots=2,
    )

    snap = reg.register_worker(spec)
    assert snap.state == WorkerState.AVAILABLE
    assert snap.is_available is True
    assert snap.active_task_count == 0

    # Assign 2 tasks
    reg.assign_task("w1", "t1")
    reg.assign_task("w1", "t2")
    snap2 = reg.get_snapshot("w1")
    assert snap2.state == WorkerState.BUSY
    assert snap2.is_available is False

    # Unassign 1 task
    reg.unassign_task("w1", "t1")
    snap3 = reg.get_snapshot("w1")
    assert snap3.state == WorkerState.AVAILABLE
    assert snap3.is_available is True

    # Deregister
    reg.deregister_worker("w1")
    assert reg.get_snapshot("w1").state == WorkerState.DEREGISTERED


def test_task_assignment_engine_selects_best_matching_worker():
    """Proves TaskAssignmentEngine selects worker with capability match and lowest slot load."""
    reg = WorkerRegistry()
    w1 = WorkerSpec(worker_id="w1", node_id="n1", capabilities=(WorkerCapability(name="extract"),), max_concurrency_slots=5)
    w2 = WorkerSpec(worker_id="w2", node_id="n2", capabilities=(WorkerCapability(name="extract"),), max_concurrency_slots=5)

    reg.register_worker(w1)
    reg.register_worker(w2)

    # Put 2 tasks on w1
    reg.assign_task("w1", "t1")
    reg.assign_task("w1", "t2")

    assignment = TaskAssignmentEngine(reg)
    spec = TaskSpec(task_id="t3", task_type="bulk", required_capabilities=("extract",))

    selected = assignment.select_worker(spec)
    assert selected.worker_id == "w2"  # w2 has lower load ratio (0/5 < 2/5)
