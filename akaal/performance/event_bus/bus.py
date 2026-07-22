"""
Internal Decoupled Performance Event Bus for Platform 6.
"""

from typing import Dict, List, Type, Callable, Any
from threading import RLock
import logging

logger = logging.getLogger("nexusforge.performance.event_bus")


class PerformanceEvent:
    """Base class for all Platform 6 performance events."""
    pass


class PerformanceEventBus:
    """Thread-safe synchronous event bus for performance notifications."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._listeners: Dict[Type[PerformanceEvent], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[PerformanceEvent], callback: Callable[[Any], None]) -> None:
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def publish(self, event: PerformanceEvent) -> None:
        event_cls = type(event)
        callbacks = []
        with self._lock:
            if event_cls in self._listeners:
                callbacks = list(self._listeners[event_cls])

        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Error executing listener {cb} for event {event_cls.__name__}: {str(e)}", exc_info=True)
