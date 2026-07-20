"""CircuitBreaker Pattern Implementation for External Service Outage Prevention."""

import threading
from enum import Enum
from typing import Callable, Any
from akaal.workflow.utils.clock import IClock, SystemClock


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Thread-safe CircuitBreaker tripping execution upon repeated service failure."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        clock: IClock | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._clock = clock or SystemClock()
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_state_change: float = float(self._clock.monotonic())
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            now = float(self._clock.monotonic())
            if self._state == CircuitState.OPEN and (now - self._last_state_change) > self.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
            return self._state

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        st = self.state
        if st == CircuitState.OPEN:
            raise RuntimeError("CircuitBreaker is OPEN - execution blocked.")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            return result
        except Exception as exc:
            with self._lock:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_state_change = float(self._clock.monotonic())
            raise exc
