"""
Unit tests for Circuit Breaker and Retry Engine.
"""

import pytest
import asyncio
from akaal.api.contracts.errors import CircuitBreakerOpenError
from akaal.api.resilience.circuit_breaker import CircuitBreaker
from akaal.api.resilience.retry import RetryPolicy


@pytest.mark.asyncio
async def test_circuit_breaker_tripping():
    cb = CircuitBreaker("test-circuit", failure_threshold=0.5, recovery_timeout_s=0.2, max_concurrency=10)

    async def failing_func():
        raise ValueError("Backend network failure")

    # Cause 5 failures
    for _ in range(5):
        with pytest.raises(ValueError):
            await cb.execute(failing_func)

    assert cb.state == "OPEN"

    # Calls while OPEN raise CircuitBreakerOpenError fast
    with pytest.raises(CircuitBreakerOpenError):
        await cb.execute(failing_func)

    # Wait for recovery timeout
    await asyncio.sleep(0.25)

    async def successful_func():
        return "OK"

    # Transitions to HALF_OPEN and then CLOSED on success
    res = await cb.execute(successful_func)
    assert res == "OK"


@pytest.mark.asyncio
async def test_retry_policy():
    retry = RetryPolicy(max_retries=2, base_delay_s=0.01, max_delay_s=0.05)
    attempts = 0

    async def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Flaky network")
        return "SUCCESS"

    res = await retry.execute(flaky_func)
    assert res == "SUCCESS"
    assert attempts == 3
