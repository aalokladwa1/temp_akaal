"""
Akaal — Scout Lifecycle Events & Event Bus
===========================================
Event infrastructure for Scout Platform lifecycle monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass
class DiscoveryEvent:
    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryStarted(DiscoveryEvent):
    def __init__(self, request_info: Dict[str, Any]):
        super().__init__("DiscoveryStarted", payload=request_info)


@dataclass
class StageStarted(DiscoveryEvent):
    def __init__(self, stage_name: str):
        super().__init__("StageStarted", payload={"stage_name": stage_name})


@dataclass
class StageCompleted(DiscoveryEvent):
    def __init__(self, stage_name: str, duration_ms: float):
        super().__init__("StageCompleted", payload={"stage_name": stage_name, "duration_ms": duration_ms})


@dataclass
class StageFailed(DiscoveryEvent):
    def __init__(self, stage_name: str, error_msg: str):
        super().__init__("StageFailed", payload={"stage_name": stage_name, "error": error_msg})


@dataclass
class DiscoveryCompleted(DiscoveryEvent):
    def __init__(self, overall_status: str, total_duration_ms: float):
        super().__init__("DiscoveryCompleted", payload={"overall_status": overall_status, "total_duration_ms": total_duration_ms})


class DiscoveryEventBus:
    """Thread-safe event bus for Scout platform notifications."""

    def __init__(self) -> None:
        self._listeners: List[Callable[[DiscoveryEvent], None]] = []

    def subscribe(self, listener: Callable[[DiscoveryEvent], None]) -> None:
        self._listeners.append(listener)

    def publish(self, event: DiscoveryEvent) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:
                pass
