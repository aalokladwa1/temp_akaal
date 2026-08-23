"""
akaalEngine.telemetry.bus.dispatcher
=====================================
InProcessEventDispatcher for fail-isolated synchronous/asynchronous event routing.
Mined from `akaal/distributed/events/events.py`.
"""

from collections import deque
import logging
from threading import RLock
import uuid
from typing import Callable, Dict, List, Optional, Type

from akaalEngine.telemetry.models.event import OperationalEvent
from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

logger = logging.getLogger("akaalEngine.telemetry.bus")


class InProcessEventDispatcher:
    """
    Fail-isolated in-process event dispatcher.
    Ensures that subscriber exceptions do not fail operational tasks or corrupt telemetry.
    """

    def __init__(self, max_history_events: int = 1000) -> None:
        self.max_history_events = max_history_events
        self._subscribers: Dict[str, Callable[[OperationalEvent], None]] = {}
        self._typed_subscribers: Dict[str, List[str]] = {}
        self._history: deque[OperationalEvent] = deque(maxlen=max_history_events)
        self._dropped_events_count: int = 0
        self._subscriber_error_count: int = 0
        self._lock = RLock()

    def subscribe(self, callback: Callable[[OperationalEvent], None], event_type: Optional[str] = None) -> str:
        with self._lock:
            sub_id = f"sub-{uuid.uuid4().hex[:8]}"
            self._subscribers[sub_id] = callback
            type_key = event_type or "*"
            self._typed_subscribers.setdefault(type_key, []).append(sub_id)
            return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        with self._lock:
            if sub_id in self._subscribers:
                del self._subscribers[sub_id]
                for sub_list in self._typed_subscribers.values():
                    if sub_id in sub_list:
                        sub_list.remove(sub_id)
                return True
            return False

    def publish(self, event: OperationalEvent) -> None:
        with self._lock:
            # Sanitize event attributes before processing
            sanitized_attrs = TelemetrySanitizer.sanitize_mapping(event.attributes)
            sanitized_event = OperationalEvent(
                name=event.name,
                metadata=event.metadata,
                attributes=sanitized_attrs,
                severity=event.severity,
            )
            self._history.append(sanitized_event)

            type_key = event.metadata.event_type or event.name
            target_subs = list(self._typed_subscribers.get(type_key, [])) + list(self._typed_subscribers.get("*", []))
            target_subs = list(dict.fromkeys(target_subs))

        # Dispatch outside main lock to prevent deadlock with subscribers
        for sub_id in target_subs:
            cb = self._subscribers.get(sub_id)
            if cb:
                try:
                    cb(sanitized_event)
                except Exception as exc:
                    with self._lock:
                        self._subscriber_error_count += 1
                    logger.error(f"[EventDispatcher] Subscriber '{sub_id}' failed on event '{event.name}': {exc}")

    def get_history(self, limit: Optional[int] = None) -> List[OperationalEvent]:
        with self._lock:
            items = list(self._history)
            if limit and limit > 0:
                return items[-limit:]
            return items

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._dropped_events_count = 0
            self._subscriber_error_count = 0

    @property
    def metrics(self) -> Dict[str, int]:
        with self._lock:
            return {
                "active_subscribers": len(self._subscribers),
                "history_count": len(self._history),
                "dropped_events_count": self._dropped_events_count,
                "subscriber_error_count": self._subscriber_error_count,
            }
