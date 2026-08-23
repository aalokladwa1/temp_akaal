"""
akaalEngine.telemetry.models.event
===================================
Standardized EventMetadata and OperationalEvent models mined from legacy `akaal/distributed/events/events.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class EventMetadata:
    """Standardized metadata for operational telemetry events."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_version: str = "1.0.0"
    event_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = ""
    causation_id: str = ""
    producer_id: str = "akaalEngine.telemetry"


@dataclass(frozen=True)
class OperationalEvent:
    """Base immutable operational event."""
    name: str
    metadata: EventMetadata = field(default_factory=EventMetadata)
    attributes: Mapping[str, Any] = field(default_factory=dict)
    severity: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    def __post_init__(self) -> None:
        if not self.metadata.event_type:
            meta = EventMetadata(
                event_id=self.metadata.event_id,
                event_version=self.metadata.event_version,
                event_type=self.name or self.__class__.__name__,
                timestamp=self.metadata.timestamp,
                correlation_id=self.metadata.correlation_id,
                causation_id=self.metadata.causation_id,
                producer_id=self.metadata.producer_id,
            )
            object.__setattr__(self, "metadata", meta)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "event_id": self.metadata.event_id,
            "event_type": self.metadata.event_type,
            "timestamp": self.metadata.timestamp,
            "correlation_id": self.metadata.correlation_id,
            "causation_id": self.metadata.causation_id,
            "producer_id": self.metadata.producer_id,
            "severity": self.severity,
            "attributes": dict(self.attributes),
        }
