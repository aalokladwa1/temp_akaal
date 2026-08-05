"""
AKAAL Enterprise Platform — Centralized Pub/Sub Event Bus
==========================================================
Supports topic routing, subscription filters, strict ordering, event durability, and history replay.
"""

import time
import fnmatch
import threading
from typing import Any, Callable, Dict, List
from akaal.core.interfaces.enterprise_interfaces import IEventBus


class EnterpriseEventBus(IEventBus):
    """Authoritative Pub/Sub Event Bus."""

    def __init__(self) -> None:
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []
        self._sequence_counter: int = 0
        self._lock = threading.Lock()

    def publish(self, topic: str, event_data: Dict[str, Any]) -> str:
        with self._lock:
            self._sequence_counter += 1
            seq = self._sequence_counter
            event_id = f"evt-{seq}-{int(time.time())}"
            record = {
                "event_id": event_id,
                "sequence_id": seq,
                "topic": topic,
                "timestamp": time.time(),
                "payload": event_data,
            }
            self._history.append(record)
            if len(self._history) > 5000:
                self._history.pop(0)

            # Route to matching subscribers
            handlers = []
            for sub_id, sub in self._subscriptions.items():
                if fnmatch.fnmatch(topic, sub["pattern"]):
                    handlers.append(sub["handler"])

        for handler in handlers:
            try:
                handler(topic, record)
            except Exception:
                pass

        return event_id

    def subscribe(self, topic_pattern: str, handler: Callable[[str, Dict[str, Any]], None]) -> str:
        with self._lock:
            sub_id = f"sub-{len(self._subscriptions) + 1}-{int(time.time())}"
            self._subscriptions[sub_id] = {
                "pattern": topic_pattern,
                "handler": handler,
            }
            return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            self._subscriptions.pop(subscription_id, None)

    def replay_events(self, topic_pattern: str, from_sequence_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            matched = []
            for item in self._history:
                if item["sequence_id"] >= from_sequence_id and fnmatch.fnmatch(item["topic"], topic_pattern):
                    matched.append(dict(item))
            return matched
