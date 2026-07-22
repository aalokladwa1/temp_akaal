"""
Enterprise Operations Event Bus.
Decoupled typed event channels for Platform 9.
"""

from typing import Dict, List, Type, Callable, Any
from threading import RLock
import time


class OperationsEvent:
    """Base class for all Platform 9 operational events."""
    def __init__(self, source_platform: str = "Platform9", correlation_id: str = "") -> None:
        self.source_platform = source_platform
        self.correlation_id = correlation_id or f"corr_{int(time.time() * 1000)}"
        self.timestamp = time.time()


class PlatformHealthChangedEvent(OperationsEvent):
    def __init__(self, platform_id: str, old_health: float, new_health: float, reason: str = "") -> None:
        super().__init__(source_platform=platform_id)
        self.platform_id = platform_id
        self.old_health = old_health
        self.new_health = new_health
        self.reason = reason


class WorkerFailedEvent(OperationsEvent):
    def __init__(self, worker_id: str, node_id: str, reason: str) -> None:
        super().__init__(source_platform="Platform2")
        self.worker_id = worker_id
        self.node_id = node_id
        self.reason = reason


class JobStartedEvent(OperationsEvent):
    def __init__(self, job_id: str, workflow_id: str) -> None:
        super().__init__(source_platform="Platform1")
        self.job_id = job_id
        self.workflow_id = workflow_id


class JobCompletedEvent(OperationsEvent):
    def __init__(self, job_id: str, success: bool, details: str = "") -> None:
        super().__init__(source_platform="Platform1")
        self.job_id = job_id
        self.success = success
        self.details = details


class IncidentOpenedEvent(OperationsEvent):
    def __init__(self, incident_id: str, title: str, severity: str) -> None:
        super().__init__(source_platform="Platform9")
        self.incident_id = incident_id
        self.title = title
        self.severity = severity


class IncidentClosedEvent(OperationsEvent):
    def __init__(self, incident_id: str, resolution_notes: str) -> None:
        super().__init__(source_platform="Platform9")
        self.incident_id = incident_id
        self.resolution_notes = resolution_notes


class AlertRaisedEvent(OperationsEvent):
    def __init__(self, alert_id: str, rule_name: str, message: str, severity: str) -> None:
        super().__init__(source_platform="Platform9")
        self.alert_id = alert_id
        self.rule_name = rule_name
        self.message = message
        self.severity = severity


class OperationsEventBus:
    """In-process thread-safe Operations Event Bus."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: Dict[Type[OperationsEvent], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[OperationsEvent], handler: Callable[[Any], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def publish(self, event: OperationsEvent) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(type(event), []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Event bus handler errors isolated
