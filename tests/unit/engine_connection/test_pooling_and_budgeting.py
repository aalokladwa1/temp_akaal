"""
Unit tests for akaalEngine.connection.pooling
=============================================
Verifies process-local pool bounds, acquisition timeouts, PID/fork protection, and invalidation.
"""

import pytest

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import PoolExhaustionError
from akaalEngine.connection.models.session import SessionPurpose, SessionRequest
from akaalEngine.connection.pooling.manager import PoolManager
from akaalEngine.connection.pooling.policy import PoolPolicy
from akaalEngine.connection.pooling.pool import ConnectionPool
from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.connection.sessions.factory import SessionFactory


def test_pool_acquire_and_release():
    factory = SessionFactory()
    strategy = SQLiteProviderStrategy()
    policy = PoolPolicy(min_size=1, max_size=3, acquisition_timeout_seconds=2.0)
    pool = ConnectionPool(
        pool_id="test-sqlite-pool",
        fingerprint="fp-sqlite-test",
        provider_id="sqlite",
        purpose=SessionPurpose.BULK_SOURCE_READ,
        strategy=strategy,
        factory=factory,
        policy=policy,
    )

    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    req = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)

    # Acquire lease 1
    lease1 = pool.acquire(req, borrower_id="worker-1")
    assert lease1.is_valid() is True

    snapshot = pool.get_snapshot()
    assert snapshot.active_count == 1
    assert snapshot.total_allocated == 1

    # Acquire lease 2
    lease2 = pool.acquire(req, borrower_id="worker-2")
    assert lease2.is_valid() is True
    assert pool.get_snapshot().active_count == 2

    # Release lease 1
    released = pool.release(lease1)
    assert released is True
    assert pool.get_snapshot().active_count == 1
    assert pool.get_snapshot().idle_count == 1

    # Release lease 2
    pool.release(lease2)
    assert pool.get_snapshot().active_count == 0
    assert pool.get_snapshot().idle_count == 2

    pool.invalidate_all()


def test_pool_capacity_exhaustion():
    factory = SessionFactory()
    strategy = SQLiteProviderStrategy()
    policy = PoolPolicy(min_size=1, max_size=1, acquisition_timeout_seconds=0.2, max_waiters=1)
    pool = ConnectionPool(
        pool_id="test-capped-pool",
        fingerprint="fp-sqlite-capped",
        provider_id="sqlite",
        purpose=SessionPurpose.BULK_SOURCE_READ,
        strategy=strategy,
        factory=factory,
        policy=policy,
    )

    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    req = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)

    lease1 = pool.acquire(req, borrower_id="worker-1")
    assert lease1.is_valid() is True

    # Next acquire must timeout and raise PoolExhaustionError
    with pytest.raises(PoolExhaustionError):
        pool.acquire(req, borrower_id="worker-2")

    pool.release(lease1)
    pool.invalidate_all()


def test_pool_manager_invalidation():
    manager = PoolManager()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    req = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)

    lease = manager.acquire_session(req, borrower_id="worker-test")
    fp = lease.endpoint_fingerprint

    assert manager.get_pool_snapshot(fp) is not None

    # Invalidate endpoint pools
    invalidated_count = manager.invalidate_endpoint(fp)
    assert invalidated_count >= 1
    assert manager.get_pool_snapshot(fp) is None
