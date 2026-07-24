"""Tests for RepairScheduler, MultiSourceRecovery, and LockManager."""

import pytest
from akaal.healing.scheduler.scheduler import RepairScheduler
from akaal.healing.recovery.multi_source import MultiSourceRecovery, RecoverySourceType
from akaal.healing.conflicts.locks import RepairLockManager


def test_repair_scheduler():
    scheduler = RepairScheduler()
    scheduler.schedule_repair("r1", {"plan": 1}, criticality="CRITICAL")
    scheduler.schedule_repair("r2", {"plan": 2}, criticality="LOW")

    first = scheduler.get_next_repair()
    assert first["plan"] == 1  # CRITICAL popped first


def test_multi_source_recovery():
    recovery = MultiSourceRecovery()
    data = recovery.fetch_recovery_data("customers", 42, RecoverySourceType.SOURCE_DB)
    assert data["table_name"] == "customers"
    assert data["source"] == "SOURCE_DB"


def test_repair_lock_manager():
    mgr = RepairLockManager(default_ttl_seconds=10)
    assert mgr.acquire_lock("table:orders", "worker_1") is True
    assert mgr.acquire_lock("table:orders", "worker_2") is False  # Lock conflict
    mgr.release_lock("table:orders", "worker_1")
    assert mgr.acquire_lock("table:orders", "worker_2") is True
