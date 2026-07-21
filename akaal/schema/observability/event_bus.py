"""
AKAAL Platform 5 — SchemaEventPublisher (Pub/Sub Event Bus)

Provides thread-safe event subscription and publishing for metadata changes and evolution steps.
"""

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable, Dict, List


@dataclass
class SchemaEvent:
    event_type: str
    payload: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class SchemaEventPublisher:
    """Thread-safe pub/sub event bus."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[SchemaEvent], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[SchemaEvent], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        event = SchemaEvent(event_type=event_type, payload=payload)
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
            wildcard_callbacks = list(self._subscribers.get("*", []))
        for cb in callbacks + wildcard_callbacks:
            try:
                cb(event)
            except Exception:
                pass
