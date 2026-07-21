"""
AKAAL Platform 5 — Refresh Coordinator & Queue

Provides single-flight concurrent refresh protection and prioritized request queues.
"""

from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional

from akaal.schema.domain.enums import RefreshState
from akaal.schema.refresh.state_machine import RefreshStateMachine


@dataclass(order=True)
class RefreshRequest:
    priority: int  # lower number = higher priority
    request_id: str = field(compare=False)
    source: str = field(compare=False, default="user")
    created_at: float = field(compare=False, default_factory=time.time)


class RefreshCoordinator:
    """Thread-safe coordinator for prioritized refresh queue and single-flight lock."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._is_refreshing = False
        self.state_machine = RefreshStateMachine()

    def enqueue_request(self, request_id: str, priority: int = 10, source: str = "user") -> RefreshRequest:
        req = RefreshRequest(priority=priority, request_id=request_id, source=source)
        self._queue.put(req)
        with self._mutex:
            if self.state_machine.state in (RefreshState.IDLE, RefreshState.COMPLETED, RefreshState.FAILED):
                self.state_machine.transition_to(RefreshState.QUEUED)
        return req

    def acquire_single_flight(self) -> bool:
        return not self._is_refreshing

    def acquire_refresh_lock(self) -> bool:
        with self._mutex:
            if self._is_refreshing:
                return False
            self._is_refreshing = True
            if self.state_machine.state in (RefreshState.IDLE, RefreshState.QUEUED, RefreshState.COMPLETED, RefreshState.FAILED):
                self.state_machine.transition_to(RefreshState.REFRESHING)
            return True

    def release_refresh_lock(self, success: bool = True) -> None:
        with self._mutex:
            self._is_refreshing = False
            target_state = RefreshState.COMPLETED if success else RefreshState.FAILED
            self.state_machine.transition_to(target_state)

    def has_pending_requests(self) -> bool:
        return not self._queue.empty()
