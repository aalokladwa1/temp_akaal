"""Resilience Mechanisms: Retries, Retry Budgets, Circuit Breakers, Bulkheads, Backpressure, and Load Shedding."""

import time
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Callable


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RetryBudgetManager:
    """Tracks retry budget to prevent retry storms."""

    def __init__(self, max_tokens: int = 100):
        self.max_tokens = max_tokens
        self.available_tokens = max_tokens
        self._lock = threading.RLock()

    def try_consume_token(self) -> bool:
        with self._lock:
            if self.available_tokens > 0:
                self.available_tokens -= 1
                return True
            return False

    def replenish_tokens(self, count: int = 1) -> None:
        with self._lock:
            self.available_tokens = min(self.max_tokens, self.available_tokens + count)


class IntelligentRetryEngine:
    """Executes intelligent retries guarded by retry budget."""

    def __init__(self, budget_manager: Optional[RetryBudgetManager] = None):
        self.budget_manager = budget_manager or RetryBudgetManager()

    def execute_with_retry(self, func: Callable[[], Any], max_retries: int = 3) -> Dict[str, Any]:
        attempts = 0
        last_error = None
        while attempts < max_retries:
            attempts += 1
            if attempts > 1 and not self.budget_manager.try_consume_token():
                return {"status": "RETRY_BUDGET_EXHAUSTED", "attempts": attempts, "result": None}
            try:
                res = func()
                self.budget_manager.replenish_tokens(1)
                return {"status": "SUCCESS", "attempts": attempts, "result": res}
            except Exception as e:
                last_error = str(e)
        return {"status": "RETRY_FAILED", "attempts": attempts, "last_error": last_error}


class CircuitBreaker:
    """Individual Circuit Breaker state machine."""

    def __init__(self, name: str, failure_threshold: int = 5, reset_timeout_sec: float = 10.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        self._lock = threading.RLock()

    def can_execute(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_state_change > self.reset_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = time.time()
                    return True
                return False
            return True  # HALF_OPEN allows probe attempt

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()


class CircuitBreakerManager:
    """Manager for multiple circuit breaker instances."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_breaker(self, name: str) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name)
            return self._breakers[name]


class BulkheadIsolationManager:
    """Bulkhead isolation pattern to constrain concurrent resource calls."""

    def __init__(self, max_concurrent_calls: int = 50):
        self.semaphore = threading.Semaphore(max_concurrent_calls)
        self.max_concurrent_calls = max_concurrent_calls

    def execute_in_bulkhead(self, func: Callable[[], Any]) -> Dict[str, Any]:
        acquired = self.semaphore.acquire(blocking=False)
        if not acquired:
            return {"status": "BULKHEAD_REJECTED", "reason": "Max concurrency exceeded"}
        try:
            res = func()
            return {"status": "SUCCESS", "result": res}
        finally:
            self.semaphore.release()


class AdaptiveBackpressureController:
    """Controls flow rate dynamically based on system throughput and lag."""

    def __init__(self):
        self.rate_limit_factor = 1.0

    def adjust_rate(self, current_lag_ms: float, error_rate_pct: float):
        if current_lag_ms > 1000.0 or error_rate_pct > 10.0:
            self.rate_limit_factor = max(0.1, self.rate_limit_factor * 0.5)
        else:
            self.rate_limit_factor = min(1.0, self.rate_limit_factor + 0.1)


class AdaptiveLoadShedder:
    """Adaptive load shedding shedding requests by priority (Critical, High, Normal, Low, Background)."""

    PRIORITY_LEVELS = {"Critical": 5, "High": 4, "Normal": 3, "Low": 2, "Background": 1}

    def should_shed_request(self, priority: str, system_load_pct: float) -> bool:
        level = self.PRIORITY_LEVELS.get(priority, 3)
        if system_load_pct > 90.0 and level <= 2:  # Shed Low and Background
            return True
        if system_load_pct > 95.0 and level <= 3:  # Shed Normal and below
            return True
        return False


class GracefulDegradationManager:
    """Manages fallback degradation responses."""

    def execute_with_fallback(self, func: Callable[[], Any], fallback_func: Callable[[], Any]) -> Dict[str, Any]:
        try:
            res = func()
            return {"status": "PRIMARY_SUCCESS", "result": res}
        except Exception:
            res_fallback = fallback_func()
            return {"status": "DEGRADED_FALLBACK", "result": res_fallback}
