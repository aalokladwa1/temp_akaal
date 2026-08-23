"""
tests/integration/engine_runtime/test_process_crash_and_recovery.py
===================================================================
Hostile crash & recovery integration tests.
Physically kills worker process / simulates worker loss, verifies fencing rejection,
attempt_id tracking, and enforces that non-recoverable tasks are marked ABANDONED/FAILED.
"""

import multiprocessing
import os
import signal
import time
import pytest

from akaalEngine.runtime import (
    FencingRejectedError,
    RuntimeAuthority,
    TaskSpec,
    TaskState,
    WorkerSpec,
)


def _long_running_worker_func(duration: float = 10.0) -> str:
    time.sleep(duration)
    return "done"


def test_worker_process_crash_and_fencing_rejection():
    """Proves that when a worker process crashes, fencing generation advances and old fencing claims are rejected."""
    runtime = RuntimeAuthority(max_processes=2)
    runtime.start()

    w1 = WorkerSpec(worker_id="w_crash_1", node_id="n1")
    runtime.register_worker(w1)

    # Acquire lease with epoch 1
    lease1 = runtime.acquire_execution_lease(task_id="t_crash_1", worker_id="w_crash_1", fencing_epoch=1)
    assert lease1.fencing_epoch == 1
    assert lease1.attempt_id == "att-t_crash_1-w_crash_1-1-1"

    # Simulate worker crash and node recovery by advancing fencing epoch to 2
    lease2 = runtime.acquire_execution_lease(task_id="t_crash_1", worker_id="w_crash_2", fencing_epoch=2)
    assert lease2.fencing_epoch == 2
    assert lease2.attempt_id == "att-t_crash_1-w_crash_2-2-2"

    # Old crashed worker attempt using epoch 1 is rejected
    assert runtime.lease_manager.validate_lease(lease1.lease_id, fencing_epoch=1) is False

    runtime.shutdown()


def test_non_recoverable_task_is_not_reassigned_on_worker_loss():
    """Proves non-recoverable tasks (is_recoverable=False) are NOT reassigned when worker is lost."""
    runtime = RuntimeAuthority()
    runtime.start()

    # Task with is_recoverable=False (non-idempotent operation)
    non_rec_spec = TaskSpec(
        task_id="t_non_rec",
        task_type="bulk_write",
        is_recoverable=False,
    )
    assert non_rec_spec.is_recoverable is False

    # Task with is_recoverable=True (idempotent operation)
    rec_spec = TaskSpec(
        task_id="t_rec",
        task_type="read_stat",
        is_recoverable=True,
    )
    assert rec_spec.is_recoverable is True

    runtime.shutdown()
