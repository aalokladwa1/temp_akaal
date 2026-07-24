"""
AKAAL Platform 7 — Domain Events.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ReliabilityEvent:
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class SLOBreachedEvent(ReliabilityEvent):
    slo_id: str
    service_id: str
    current_val: float


@dataclass(frozen=True)
class IncidentTriggeredEvent(ReliabilityEvent):
    incident_id: str
    severity: str


@dataclass(frozen=True)
class MaintenanceStartedEvent(ReliabilityEvent):
    window_id: str
    service_id: str
