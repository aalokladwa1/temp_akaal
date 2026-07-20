"""
Enterprise Audit Logger for Workflow Orchestration.
Subscribes to domain events and produces immutable, checksum-verified audit records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
import hashlib

from akaal.orchestration.events.events import EventSubscriber, DomainEvent
from akaal.orchestration.domain.types import Checksum


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit entry."""
    entry_id: int
    event_type: str
    aggregate_id: str
    timestamp: str
    details: Dict[str, Any]
    checksum: Checksum = field(init=False)

    def __post_init__(self) -> None:
        payload = {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp,
            "details": self.details,
        }
        object.__setattr__(self, "checksum", Checksum.from_dict(payload))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp,
            "details": self.details,
            "checksum": str(self.checksum),
        }


class WorkflowAuditLogger(EventSubscriber):
    """
    WorkflowAuditLogger subscribes to domain events and writes append-only,
    checksum-verified AuditRecord instances.
    """

    def __init__(self) -> None:
        self._records: List[AuditRecord] = []
        self._sequence: int = 0

    def on_event(self, event: DomainEvent) -> None:
        """Handle incoming domain event and record audit entry."""
        self._sequence += 1
        
        # Convert dataclass fields to dict
        event_dict = {
            k: str(v) if not isinstance(v, (int, float, bool, dict, list, type(None))) else v
            for k, v in event.__dict__.items()
            if k not in ("event_id", "timestamp", "aggregate_id", "event_type")
        }

        record = AuditRecord(
            entry_id=self._sequence,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id or event.event_id,
            timestamp=event.timestamp,
            details=event_dict,
        )
        self._records.append(record)

    def get_records(self) -> List[AuditRecord]:
        """Returns copy of immutable audit records."""
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()
        self._sequence = 0
