"""
Akaal — Advisory Event
======================
Immutable platform lifecycle event record.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class AdvisoryEvent:
    """Immutable event payload."""
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "AdvisorPlatform"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "source": self.source,
        }
