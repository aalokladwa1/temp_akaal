"""
AKAAL Platform 6 — Domain Events.
"""

from dataclasses import dataclass
import datetime
from typing import Dict, Any


@dataclass(frozen=True)
class GovernanceEvent:
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class PolicyCreatedEvent(GovernanceEvent):
    policy_id: str
    version: str


@dataclass(frozen=True)
class DecisionRecordedEvent(GovernanceEvent):
    decision_id: str
    outcome: str
    block_hash: str


@dataclass(frozen=True)
class OverrideTriggeredEvent(GovernanceEvent):
    override_id: str
    authorized_by: str
    reason: str
