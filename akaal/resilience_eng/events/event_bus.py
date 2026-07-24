"""Resilience Engineering Event Types, Event Bus, Publishers, and Subscribers."""

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable, Optional
from enum import Enum


class ResilienceEventType(str, Enum):
    EXPERIMENT_SUBMITTED = "EXPERIMENT_SUBMITTED"
    EXPERIMENT_APPROVED = "EXPERIMENT_APPROVED"
    EXPERIMENT_REJECTED = "EXPERIMENT_REJECTED"
    ISOLATION_CREATED = "ISOLATION_CREATED"
    RESOURCES_RESERVED = "RESOURCES_RESERVED"
    TWIN_SIMULATION_COMPLETE = "TWIN_SIMULATION_COMPLETE"
    EXPERIMENT_STARTED = "EXPERIMENT_STARTED"
    FAULT_INJECTED = "FAULT_INJECTED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_VALIDATED = "RECOVERY_VALIDATED"
    RECOVERY_CERTIFIED = "RECOVERY_CERTIFIED"
    CONFIDENCE_COMPUTED = "CONFIDENCE_COMPUTED"
    REPORT_GENERATED = "REPORT_GENERATED"
    MATURITY_ASSESSED = "MATURITY_ASSESSED"
    PROVENANCE_RECORDED = "PROVENANCE_RECORDED"
    EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
    EXPERIMENT_ARCHIVED = "EXPERIMENT_ARCHIVED"
    SECURITY_AUTHORIZED = "SECURITY_AUTHORIZED"
    TAXONOMY_CLASSIFIED = "TAXONOMY_CLASSIFIED"
    EXPERIMENT_REPLAYED = "EXPERIMENT_REPLAYED"


@dataclass
class ResilienceEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: ResilienceEventType = ResilienceEventType.EXPERIMENT_SUBMITTED
    experiment_id: str = "exp_001"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ResilienceEventBus:
    """Thread-safe resilience event bus with typed subscriptions."""

    def __init__(self):
        self._subscribers: Dict[ResilienceEventType, List[Callable]] = {}
        self._published: List[ResilienceEvent] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: ResilienceEventType, handler: Callable[[ResilienceEvent], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def publish(self, event: ResilienceEvent) -> None:
        with self._lock:
            self._published.append(event)
            handlers = list(self._subscribers.get(event.event_type, []))
        for handler in handlers:
            handler(event)

    def published_count(self) -> int:
        with self._lock:
            return len(self._published)

    def get_published(self) -> List[ResilienceEvent]:
        with self._lock:
            return list(self._published)
