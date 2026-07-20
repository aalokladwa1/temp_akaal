"""Decoupled Event Dispatcher Interfaces and In-Memory Adapter."""

import threading
from typing import Callable, Dict, List, Protocol
from akaal.workflow.events.events import WorkflowEvent


class IEventDispatcher(Protocol):
    """Abstract interface decoupling Workflow Engine from event transport mechanics."""

    def dispatch(self, event: WorkflowEvent) -> None:
        """Dispatch a domain event to all subscribed handlers."""
        ...

    def subscribe(self, event_type: str, handler: Callable[[WorkflowEvent], None]) -> None:
        """Register a handler callback for an event type."""
        ...


class InMemoryEventDispatcher(IEventDispatcher):
    """In-memory event dispatcher for decoupled local domain event handling."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[WorkflowEvent], None]]] = {}
        self._lock = threading.Lock()
        self._dispatched_events: List[WorkflowEvent] = []

    def subscribe(self, event_type: str, handler: Callable[[WorkflowEvent], None]) -> None:
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def dispatch(self, event: WorkflowEvent) -> None:
        with self._lock:
            self._dispatched_events.append(event)
            handlers = list(self._handlers.get(event.event_type, []))
            wildcard_handlers = list(self._handlers.get("*", []))

        all_handlers = handlers + wildcard_handlers
        for handler in all_handlers:
            try:
                handler(event)
            except Exception:
                # Event dispatch should not crash core workflow execution
                pass

    @property
    def dispatched_events(self) -> tuple[WorkflowEvent, ...]:
        with self._lock:
            return tuple(self._dispatched_events)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._dispatched_events.clear()
