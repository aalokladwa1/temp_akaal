"""Healing event types and definitions."""

import time
import uuid
from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, field


class HealingEventType(str, Enum):
    REPAIR_STARTED = "RepairStarted"
    REPAIR_COMPLETED = "RepairCompleted"
    REPAIR_FAILED = "RepairFailed"
    REPAIR_ROLLED_BACK = "RepairRolledBack"
    REPAIR_VERIFIED = "RepairVerified"
    APPROVAL_REQUESTED = "ApprovalRequested"
    APPROVAL_GRANTED = "ApprovalGranted"
    APPROVAL_REJECTED = "ApprovalRejected"
    EMERGENCY_STOP = "EmergencyStop"
    KNOWLEDGE_UPDATED = "KnowledgeUpdated"
    RECOMMENDATION_GENERATED = "RecommendationGenerated"
    PATTERN_LEARNED = "PatternLearned"


@dataclass
class HealingEvent:
    """Event instance published on HealingEventBus."""

    event_type: HealingEventType
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "akaal.healing"
