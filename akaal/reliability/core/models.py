"""Core Data Models and Enums for Enterprise Reliability Platform."""

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class ReliabilityStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class ReliabilityOutcome(str, Enum):
    HEALTHY = "HEALTHY"
    RECOVERED = "RECOVERED"
    RETRIED = "RETRIED"
    CIRCUIT_OPENED = "CIRCUIT_OPENED"
    SHED = "SHED"
    FAILED = "FAILED"


@dataclass
class ReliabilityAction:
    """Individual reliability or recovery action."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str = "Cap 1"
    target_component: str = "database_pool"
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReliabilityPlan:
    """Execution plan containing reliability actions."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: List[ReliabilityAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class ReliabilityResult:
    """Result of domain-driven reliability execution."""

    domain_name: str
    capabilities_executed: List[str]
    status: ReliabilityStatus
    outcome: ReliabilityOutcome
    total_actions: int
    successful_actions: int
    failed_actions: int = 0
    confidence_score: float = 100.0
    execution_time_ms: float = 0.0
    action_details: List[Dict[str, Any]] = field(default_factory=list)
