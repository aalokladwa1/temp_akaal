"""
Unit tests for Concurrency Locks, OCC, Deadlock Detection, and Enterprise Recovery Manager.
"""

import pytest

from akaal.schema.concurrency.deadlock import DeadlockDetector
from akaal.schema.concurrency.lock_manager import SchemaLockManager
from akaal.schema.concurrency.occ import OptimisticConcurrencyController
from akaal.schema.domain.enums import FailureClass
from akaal.schema.domain.errors import ConcurrencyError, VersionConflictError
from akaal.schema.recovery.manager import RecoveryManager


def test_schema_lock_manager_exclusive_and_shared_locks():
    lm = SchemaLockManager(default_timeout_sec=0.1)

    assert lm.acquire_table_lock("users", owner_id="tx-1", exclusive=True) is True

    # Second exclusive lock times out
    with pytest.raises(ConcurrencyError):
        lm.acquire_table_lock("users", owner_id="tx-2", exclusive=True, timeout_sec=0.05)

    lm.release_table_lock("users", owner_id="tx-1")

    # Now tx-2 can acquire
    assert lm.acquire_table_lock("users", owner_id="tx-2", exclusive=False) is True


def test_optimistic_concurrency_controller_versions():
    occ = OptimisticConcurrencyController()
    v1 = occ.get_version("users")
    assert v1 == 1

    v2 = occ.validate_and_increment("users", expected_version=1)
    assert v2 == 2

    with pytest.raises(VersionConflictError):
        occ.validate_and_increment("users", expected_version=1)


def test_deadlock_detector_cycle_detection():
    detector = DeadlockDetector()
    detector.add_wait_edge("tx-1", "tx-2")
    detector.add_wait_edge("tx-2", "tx-3")
    detector.add_wait_edge("tx-3", "tx-1")

    cycle = detector.detect_deadlock("tx-1")
    assert cycle is not None
    assert len(cycle) >= 3


def test_recovery_manager_failure_modes():
    rm = RecoveryManager()
    res1 = rm.handle_failure(FailureClass.VALIDATION_FAILURE, Exception("Syntax error"))
    assert res1.recovered is False

    res2 = rm.handle_failure(FailureClass.DATABASE_FAILURE, Exception("Network disconnect"))
    assert res2.recovered is True
