"""
akaalEngine.extensions.lifecycle.notifications
==============================================
Internal typed notification dispatcher for Extensions Authority lifecycle events.
Ensures observer exceptions are safely logged and never corrupt core registry state.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, List, Optional

from akaalEngine.extensions.models.events import ExtensionEvent

logger = logging.getLogger(__name__)

ExtensionEventListener = Callable[[ExtensionEvent], None]


class NotificationDispatcher:
    """
    Thread-safe internal event dispatcher for extension lifecycle notifications.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listeners: List[ExtensionEventListener] = []

    def subscribe(self, listener: ExtensionEventListener) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: ExtensionEventListener) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def emit(self, event: ExtensionEvent) -> None:
        """Emits an event to all subscribed listeners, isolating listener exceptions."""
        with self._lock:
            listeners_snapshot = list(self._listeners)

        for listener in listeners_snapshot:
            try:
                listener(event)
            except Exception as exc:
                logger.warning(
                    "Error executing extension event listener for %s: %s",
                    event.event_type.value,
                    exc,
                    exc_info=True,
                )


default_notification_dispatcher = NotificationDispatcher()
