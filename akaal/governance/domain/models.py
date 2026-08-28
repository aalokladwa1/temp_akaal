"""
AKAAL Platform 6 — Enterprise Governance Immutable Domain Models.
"""

from dataclasses import dataclass, field
import datetime
from typing import List, Dict, Any, Optional

from akaal.governance.domain.enums import (
    ApprovalStatus,
    EmergencyReason,
    LifecycleState,
    PolicyCategory,
    RiskLevel,
    SoDConflictType,
)


@dataclass(frozen=True)
class EnterprisePolicy:
    policy_id: str
    name: str
    version: str
    category: PolicyCategory
    declarative_rule: str
    owner_id: str
    effective_from: str
    expires_at: Optional[str]
    risk_level: RiskLevel
    state: LifecycleState = LifecycleState.ACTIVE


@dataclass(frozen=True)
class SoDRule:
    rule_id: str
    role_a: str
    role_b: str
    forbidden_actions: List[str] = field(default_factory=list)
    description: str = ""
    is_active: bool = True


@dataclass(frozen=True)
class ApprovalStep:
    step_id: str
    level: int
    required_role: str
    approver_id: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_at: Optional[str] = None
    comments: Optional[str] = None


@dataclass(frozen=True)
class ApprovalWorkflow:
    workflow_id: str
    operation_type: str
    target_platform: str
    requester_id: str
    steps: List[ApprovalStep]
    risk_score: float
    is_four_eyes_required: bool
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = ""
    sla_due_at: str = ""


@dataclass(frozen=True)
class HumanCheckpoint:
    checkpoint_id: str
    workflow_id: str
    verification_type: str
    verifier_id: Optional[str]
    status: ApprovalStatus
    signed_off_at: Optional[str]


@dataclass(frozen=True)
class EmergencyOverride:
    override_id: str
    operation_id: str
    justification: str
    reason_category: EmergencyReason
    authorized_by: str
    valid_until: str
    is_active: bool = True


@dataclass(frozen=True)
class ExceptionWaiver:
    waiver_id: str
    policy_id: str
    requested_by: str
    approved_by: Optional[str]
    justification: str
    granted_at: str
    expires_at: str
    is_active: bool = True


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    standard_name: str
    regulation_code: str
    validation_logic: str
    state: LifecycleState = LifecycleState.ACTIVE


@dataclass(frozen=True)
class EvidenceArtifact:
    evidence_id: str
    artifact_type: str
    storage_uri: str
    content_hash: str
    created_at: str


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    workflow_id: str
    target_platform: str
    operation_type: str
    outcome: ApprovalStatus
    decision_rationale: str
    evaluated_policies: List[str]
    evidence_hashes: List[str]
    timestamp: str
    block_hash: str


@dataclass(frozen=True)
class GovernanceHealthScore:
    health_score: float
    active_violations: int
    sla_compliance_rate: float
    unresolved_exceptions: int
    posture_status: str
    calculated_at: str


@dataclass(frozen=True)
class ImpactReport:
    report_id: str
    target_artifact_id: str
    change_type: str
    affected_systems: List[str]
    affected_policies: List[str]
    risk_delta: float
    compliance_delta: float
    estimated_volume_change: float
    executive_summary: str


@dataclass(frozen=True)
class GovernanceDependencyNode:
    artifact_id: str
    artifact_type: str
    dependencies: List[str]  # List of artifact_ids depended on


@dataclass(frozen=True)
class LifecycleTransition:
    transition_id: str
    artifact_id: str
    from_state: LifecycleState
    to_state: LifecycleState
    actor_id: str
    timestamp: str
    justification: str
