"""ReplicationEventBus and Subscribers for Platform 3."""

import inspect
import threading
from typing import Callable, Dict, List
from akaal.replication.events.events import ReplicationEvent, ReplicationEventType


class ReplicationEventBus:
    """Thread-safe event bus for broadcasting replication lifecycle events."""

    def __init__(self):
        self._subscribers: Dict[ReplicationEventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: ReplicationEventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable) -> None:
        with self._lock:
            self._global_subscribers.append(callback)

    async def publish(self, event: ReplicationEvent) -> None:
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

    async def publish_replication_started(self, domain_name: str) -> None:
        await self.publish(ReplicationEvent(ReplicationEventType.REPLICATION_STARTED, {"domain": domain_name}))

    async def publish_replication_completed(self, domain_name: str, action_count: int) -> None:
        await self.publish(ReplicationEvent(ReplicationEventType.REPLICATION_COMPLETED, {"domain": domain_name, "actions": action_count}))


class ReplicationMetricsSubscriber:
    """Subscriber collecting event stats."""

    def __init__(self):
        self.event_counts: Dict[ReplicationEventType, int] = {}
        self._lock = threading.RLock()

    def on_event(self, event: ReplicationEvent) -> None:
        with self._lock:
            self.event_counts[event.event_type] = self.event_counts.get(event.event_type, 0) + 1
