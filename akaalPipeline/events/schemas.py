"""akaalPipeline.events.schemas
==============================
Domain event, integration event, and engine event proposal schemas.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


from akaalPipeline.contracts.serialization import deep_freeze


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    aggregate_id: str
    event_type: str
    payload: Mapping[str, Any]
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", deep_freeze(self.payload))

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> DomainEvent:
        return cls(
            event_id=f"evt-{uuid.uuid4().hex}",
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )


@dataclass(frozen=True)
class IntegrationEvent:
    event_id: str
    event_type: str
    payload: Mapping[str, Any]
    correlation_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", deep_freeze(self.payload))


@dataclass(frozen=True)
class EngineEventProposal:
    proposal_id: str
    engine_binding_id: str
    attempt_id: str
    engine_invocation_id: str
    lease_id: str
    fence_epoch: int
    initialization_fingerprint: str
    graph_node_id: str
    proposed_event_type: str
    payload: Mapping[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", deep_freeze(self.payload))
