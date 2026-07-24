"""ReliabilityEventBus and Event Publishers/Subscribers."""

import inspect
import threading
from typing import Callable, Dict, List
from akaal.reliability.events.events import ReliabilityEvent, ReliabilityEventType


class ReliabilityEventBus:
    """Thread-safe event bus for broadcasting reliability lifecycle events."""

    def __init__(self):
        self._subscribers: Dict[ReliabilityEventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: ReliabilityEventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable) -> None:
        with self._lock:
            self._global_subscribers.append(callback)

    async def publish(self, event: ReliabilityEvent) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event.event_type, [])) + list(self._global_subscribers)

        for cb in callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception:
                pass

    async def publish_retry_started(self, domain_name: str) -> None:
        await self.publish(ReliabilityEvent(ReliabilityEventType.RETRY_STARTED, {"domain": domain_name}))

    async def publish_recovery_started(self, domain_name: str) -> None:
        await self.publish(ReliabilityEvent(ReliabilityEventType.RECOVERY_STARTED, {"domain": domain_name}))

    async def publish_diagnostics_completed(self, domain_name: str) -> None:
        await self.publish(ReliabilityEvent(ReliabilityEventType.DIAGNOSTICS_COMPLETED, {"domain": domain_name}))


class ReliabilityMetricsSubscriber:
    """Subscriber collecting event stats."""

    def __init__(self):
        self.event_counts: Dict[ReliabilityEventType, int] = {}
        self._lock = threading.RLock()

    def on_event(self, event: ReliabilityEvent) -> None:
        with self._lock:
            self.event_counts[event.event_type] = self.event_counts.get(event.event_type, 0) + 1
