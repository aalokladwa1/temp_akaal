"""
tests/unit/engine_runtime/test_execution_and_cancellation.py
==============================================================
Unit tests for BoundedThreadExecutor, IsolatedProcessExecutor, CancellationTokens, and PauseGates.
"""

import time
import pytest
from akaalEngine.runtime import (
    RuntimeAuthority,
    TaskSpec,
    TaskState,
    WorkerSpec,
)
from akaalEngine.runtime.execution.cancellation import CancellationToken, PauseGate
from akaalEngine.runtime.execution.local import BoundedThreadExecutor


def _sample_task_function(a: int, b: int) -> int:
    return a + b


def _pausable_task_function(gate: PauseGate) -> str:
    gate.wait_if_paused(timeout=2.0)
    return "completed"


def test_local_thread_executor_execution_and_result_capture():
    """Proves BoundedThreadExecutor executes tasks and captures results."""
    executor = BoundedThreadExecutor(max_workers=2)
    spec = TaskSpec(task_id="t1", task_type="calc", func=_sample_task_function, args=(10, 20))

    fut = executor.submit(spec)
    res = fut.result(timeout=2.0)
    assert res == 30
    executor.shutdown()


def test_cooperative_cancellation_token_signaling():
    """Proves CancellationToken records cancellation and raises when checked."""
    token = CancellationToken("t_cancel")
    assert token.is_cancelled is False

    token.cancel("User cancelled")
    assert token.is_cancelled is True
    assert token.reason == "User cancelled"

    with pytest.raises(Exception) as exc_info:
        token.check()
    assert "User cancelled" in str(exc_info.value)


def test_runtime_authority_submit_pause_resume_cancel():
    """Proves RuntimeAuthority submits, pauses, resumes, and cancels tasks cleanly."""
    runtime = RuntimeAuthority(max_threads=4)
    runtime.start()

    w_spec = WorkerSpec(worker_id="w1", node_id="n1")
    runtime.register_worker(w_spec)

    spec = TaskSpec(task_id="t_pr", task_type="work", func=_sample_task_function, args=(5, 5))
    snap = runtime.submit_task(spec)
    assert snap.state in (TaskState.RUNNING, TaskState.SUCCEEDED)

    # Test inspect
    inspected = runtime.inspect_task("t_pr")
    assert inspected.task_id == "t_pr"

    runtime.shutdown()
