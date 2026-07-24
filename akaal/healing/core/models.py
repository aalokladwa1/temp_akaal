"""Data models for AKAAL Self-Healing Platform."""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class HealingStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    PLANNING = "PLANNING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ESCALATED = "ESCALATED"


class RepairOutcome(str, Enum):
    REPAIRED = "REPAIRED"
    RETRIED = "RETRIED"
    ROLLED_BACK = "ROLLED_BACK"
    ESCALATED = "ESCALATED"
    SKIPPED = "SKIPPED"


@dataclass
class ConfidenceScore:
    """Calculated repair confidence metrics."""

    quality_score: float = 100.0  # 0 to 100
    risk_score: float = 0.0      # 0 to 100
    overall_confidence: float = 100.0
    coverage: float = 100.0


@dataclass
class RepairAction:
    """Represents a specific idempotent repair action."""

    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    capability_id: str = ""
    target_table: str = ""
    target_column: Optional[str] = None
    target_row_id: Optional[Any] = None
    repair_type: str = "AUTO"
    sql_command: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = field(default_factory=lambda: uuid.uuid4().hex)
    is_executed: bool = False


@dataclass
class HealingStep:
    """Single step in a multi-stage repair workflow."""

    step_id: str
    name: str
    actions: List[RepairAction]
    dependencies: List[str] = field(default_factory=list)
    status: HealingStatus = HealingStatus.INITIALIZED
    execution_time_ms: float = 0.0


@dataclass
class RollbackManifest:
    """Manifest tracking target rows and state for partial/selective rollback."""

    manifest_id: str = field(default_factory=lambda: f"roll_{uuid.uuid4().hex[:8]}")
    target_tables: List[str] = field(default_factory=list)
    row_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class HealingPlan:
    """Complete dry-run or live repair plan generated prior to execution."""

    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    validation_evidence_id: str = ""
    steps: List[HealingStep] = field(default_factory=list)
    confidence: ConfidenceScore = field(default_factory=ConfidenceScore)
    requires_approval: bool = False
    approval_level: str = "SINGLE"
    is_approved: bool = True
    rollback_manifest: Optional[RollbackManifest] = None


@dataclass
class HealingResult:
    """Result returned by domain healers and repair orchestrator."""

    domain_name: str
    capabilities_executed: List[str]
    status: HealingStatus
    outcome: RepairOutcome
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    confidence_score: float = 100.0
    execution_time_ms: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def merge(self, other: "HealingResult") -> "HealingResult":
        """Merge another result into this one."""
        self.capabilities_executed = list(set(self.capabilities_executed + other.capabilities_executed))
        self.total_actions += other.total_actions
        self.successful_actions += other.successful_actions
        self.failed_actions += other.failed_actions
        self.execution_time_ms += other.execution_time_ms
        self.metrics.update(other.metrics)

        if other.status == HealingStatus.FAILED or self.status == HealingStatus.FAILED:
            self.status = HealingStatus.FAILED
        self.confidence_score = min(self.confidence_score, other.confidence_score)
        return self
