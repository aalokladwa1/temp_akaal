"""
Unit tests for RateLimiter and IdempotencyManager.
"""

import pytest
from akaal.api.contracts.errors import RateLimitExceededError, IdempotencyError
from akaal.api.middleware.idempotency import IdempotencyManager
from akaal.api.middleware.rate_limit import RateLimiter


def test_rate_limiter_quota():
    limiter = RateLimiter(requests_per_window=3, window_seconds=60)
    key = "tenant-1:jobs"

    limit, rem, reset = limiter.check_rate_limit(key)
    assert rem == 2
    limit, rem, reset = limiter.check_rate_limit(key)
    assert rem == 1
    limit, rem, reset = limiter.check_rate_limit(key)
    assert rem == 0

    with pytest.raises(RateLimitExceededError):
        limiter.check_rate_limit(key)


def test_idempotency_manager_flow():
    mgr = IdempotencyManager(lock_ttl_seconds=10, result_ttl_seconds=100)
    key = "idem-uuid-999"

    # First attempt acquires lock
    cached = mgr.acquire_or_get_cached(key)
    assert cached is None

    # Concurrent attempt raises IdempotencyError
    with pytest.raises(IdempotencyError):
        mgr.acquire_or_get_cached(key)

    # Save completed write result
    mgr.save_response(key, 201, {"job_id": "job-created-999"})

    # Subsequent attempt returns cached result
    cached = mgr.acquire_or_get_cached(key)
    assert cached is not None
    status_code, body = cached
    assert status_code == 201
    assert body["job_id"] == "job-created-999"
