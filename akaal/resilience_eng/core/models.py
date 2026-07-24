"""Core Data Models and Enums for Enterprise Resilience Validation Platform."""

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class ExperimentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResilienceEngStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    REJECTED = "REJECTED"


class ResilienceEngOutcome(str, Enum):
    VALIDATED = "VALIDATED"
    CERTIFIED = "CERTIFIED"
    HEALED = "HEALED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass
class ResilienceExperimentAction:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str = "Cap 1"
    target_component: str = "database_primary"
    severity: ExperimentSeverity = ExperimentSeverity.MEDIUM
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResilienceExperimentPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_name: str = "Chaos_DB_Latency_Injection"
    actions: List[ResilienceExperimentAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class ResilienceExperimentResult:
    domain_name: str
    capabilities_executed: List[str]
    status: ResilienceEngStatus
    outcome: ResilienceEngOutcome
    total_actions: int
    successful_actions: int
    failed_actions: int = 0
    confidence_score: float = 100.0
    resilience_score: float = 98.5
    execution_time_ms: float = 0.0
    action_details: List[Dict[str, Any]] = field(default_factory=list)
