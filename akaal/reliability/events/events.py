"""Typed Reliability Event Models and ReliabilityEventType Enum (15 Event Types)."""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class ReliabilityEventType(str, Enum):
    FAILURE_DETECTED = "FAILURE_DETECTED"
    RETRY_STARTED = "RETRY_STARTED"
    RETRY_COMPLETED = "RETRY_COMPLETED"
    RETRY_FAILED = "RETRY_FAILED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    ROLLBACK_STARTED = "ROLLBACK_STARTED"
    ROLLBACK_COMPLETED = "ROLLBACK_COMPLETED"
    CIRCUIT_OPENED = "CIRCUIT_OPENED"
    CIRCUIT_CLOSED = "CIRCUIT_CLOSED"
    BULKHEAD_ACTIVATED = "BULKHEAD_ACTIVATED"
    HEALTH_CHANGED = "HEALTH_CHANGED"
    DIAGNOSTICS_COMPLETED = "DIAGNOSTICS_COMPLETED"
    POLICY_APPLIED = "POLICY_APPLIED"
    INCIDENT_ESCALATED = "INCIDENT_ESCALATED"


@dataclass
class ReliabilityEvent:
    event_type: ReliabilityEventType
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
