"""akaalPipeline.state.history
=============================
Lifecycle history records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from akaalPipeline.security.context import PipelineActorContext


@dataclass(frozen=True)
class LifecycleHistoryRecord:
    history_id: str
    migration_id: str
    from_state: str
    to_state: str
    actor: PipelineActorContext
    reason: str
    correlation_id: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "history_id": self.history_id,
            "migration_id": self.migration_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor.to_dict(),
            "reason": self.reason,
            "correlation_id": self.correlation_id,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LifecycleHistoryRecord:
        return cls(
            history_id=data["history_id"],
            migration_id=data["migration_id"],
            from_state=data["from_state"],
            to_state=data["to_state"],
            actor=PipelineActorContext.from_dict(data["actor"]),
            reason=data["reason"],
            correlation_id=data.get("correlation_id"),
            details=data.get("details", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
