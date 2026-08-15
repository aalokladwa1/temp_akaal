"""
AKAAL CDC Failback Decision Engine & Primary Role Authority.
=============================================================
Manages primary role states (SOURCE_PRIMARY, CUTOVER_TRANSITION, TARGET_PRIMARY, FAILBACK_TRANSITION, UNKNOWN),
evaluates pre-cutover abort safety, and performs post-cutover failback eligibility checks.
Fails closed with MANUAL_INTERVENTION_REQUIRED when unsafe divergence is detected.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.sync.cutover_plan import CDCCutoverPlan, CutoverPhase

logger = logging.getLogger("akaal.cdc.sync.failback")


class PrimaryRoleState(str, Enum):
    """Authoritative primary database role tracking."""
    SOURCE_PRIMARY = "SOURCE_PRIMARY"
    CUTOVER_TRANSITION = "CUTOVER_TRANSITION"
    TARGET_PRIMARY = "TARGET_PRIMARY"
    FAILBACK_TRANSITION = "FAILBACK_TRANSITION"
    UNKNOWN = "UNKNOWN"


class CDCFailbackClassification(str, Enum):
    """Classification of failback / recovery eligibility."""
    PRE_CUTOVER_ABORT = "PRE_CUTOVER_ABORT"
    POST_CUTOVER_SAFE_FAILBACK = "POST_CUTOVER_SAFE_FAILBACK"
    POST_CUTOVER_REVERSE_SYNC_REQUIRED = "POST_CUTOVER_REVERSE_SYNC_REQUIRED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"
    FAILBACK_NOT_ALLOWED = "FAILBACK_NOT_ALLOWED"


class CDCRecoveryPlan:
    """Identity-bound durable recovery / failback plan."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        cutover_plan_id: str,
        fencing_epoch: int,
        current_primary: PrimaryRoleState = PrimaryRoleState.TARGET_PRIMARY,
        previous_primary: PrimaryRoleState = PrimaryRoleState.SOURCE_PRIMARY,
        last_safe_checkpoint: Optional[str] = None,
        recovery_plan_id: Optional[str] = None,
    ) -> None:
        self.recovery_plan_id = recovery_plan_id or f"plan-rec-{uuid.uuid4().hex[:8]}"
        self.identity = identity
        self.cutover_plan_id = cutover_plan_id
        self.fencing_epoch = fencing_epoch
        self.current_primary = current_primary
        self.previous_primary = previous_primary
        self.last_safe_checkpoint = last_safe_checkpoint
        self.is_executed = False
        self.executed_at: Optional[str] = None
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovery_plan_id": self.recovery_plan_id,
            "identity": self.identity.to_dict(),
            "cutover_plan_id": self.cutover_plan_id,
            "fencing_epoch": self.fencing_epoch,
            "current_primary": self.current_primary.value if isinstance(self.current_primary, Enum) else self.current_primary,
            "previous_primary": self.previous_primary.value if isinstance(self.previous_primary, Enum) else self.previous_primary,
            "last_safe_checkpoint": self.last_safe_checkpoint,
            "is_executed": self.is_executed,
            "executed_at": self.executed_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCRecoveryPlan':
        d = dict(data)
        if "identity" in d and isinstance(d["identity"], dict):
            d["identity"] = CDCEventIdentity.from_dict(d["identity"])
        if "current_primary" in d and isinstance(d["current_primary"], str):
            d["current_primary"] = PrimaryRoleState(d["current_primary"])
        if "previous_primary" in d and isinstance(d["previous_primary"], str):
            d["previous_primary"] = PrimaryRoleState(d["previous_primary"])
        return cls(**d)


class CDCFailbackDecisionEngine:
    """Decision engine for pre-cutover abort and post-cutover failback evaluation."""

    def __init__(self, cdc_session_id: str) -> None:
        self.cdc_session_id = cdc_session_id
        self.current_role = PrimaryRoleState.SOURCE_PRIMARY

    def set_role(self, role: PrimaryRoleState) -> None:
        logger.info(f"[PrimaryRoleState] Session '{self.cdc_session_id}' role updated: '{self.current_role.value}' -> '{role.value}'.")
        self.current_role = role

    def evaluate_pre_cutover_abort(self, cutover_plan: Optional[CDCCutoverPlan]) -> Dict[str, Any]:
        """Evaluates pre-cutover abort safety."""
        if cutover_plan and cutover_plan.is_committed:
            return {
                "cdc_session_id": self.cdc_session_id,
                "can_abort": False,
                "classification": CDCFailbackClassification.FAILBACK_NOT_ALLOWED.value,
                "reason": "CUTOVER_ALREADY_COMMITTED",
                "action_required": "USE_POST_CUTOVER_FAILBACK",
            }
        return {
            "cdc_session_id": self.cdc_session_id,
            "can_abort": True,
            "classification": CDCFailbackClassification.PRE_CUTOVER_ABORT.value,
            "reason": "PRE_CUTOVER_ABORT_SAFE",
            "action_required": "RESTORE_SYNCHRONIZATION_LIFECYCLE",
        }

    def evaluate_post_cutover_failback(
        self,
        cutover_plan: Optional[CDCCutoverPlan],
        target_received_post_cutover_writes: bool = False,
        source_received_post_cutover_writes: bool = False,
        reverse_cdc_available: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates post-cutover failback safety.
        Fails closed with MANUAL_INTERVENTION_REQUIRED if data divergence is possible.
        """
        blockers: List[str] = []
        classification = CDCFailbackClassification.POST_CUTOVER_SAFE_FAILBACK

        if not cutover_plan or not cutover_plan.is_committed:
            blockers.append("CUTOVER_NOT_COMMITTED")
            classification = CDCFailbackClassification.FAILBACK_NOT_ALLOWED

        if target_received_post_cutover_writes and not reverse_cdc_available:
            blockers.append("POST_CUTOVER_TARGET_WRITES_WITHOUT_REVERSE_CDC")
            classification = CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED
        elif target_received_post_cutover_writes and reverse_cdc_available and not source_received_post_cutover_writes:
            classification = CDCFailbackClassification.POST_CUTOVER_REVERSE_SYNC_REQUIRED

        if target_received_post_cutover_writes and source_received_post_cutover_writes:
            blockers.append("SPLIT_BRAIN_BOTH_DATABASES_RECEIVED_WRITES")
            classification = CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED

        if self.current_role == PrimaryRoleState.UNKNOWN:
            blockers.append("UNKNOWN_AUTHORITATIVE_ROLE_STATE")
            classification = CDCFailbackClassification.MANUAL_INTERVENTION_REQUIRED

        if blockers:
            return {
                "cdc_session_id": self.cdc_session_id,
                "safe_auto_failback": False,
                "classification": classification.value if isinstance(classification, Enum) else classification,
                "status": "MANUAL_INTERVENTION_REQUIRED",
                "blockers": blockers,
                "current_role": self.current_role.value,
                "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        if classification == CDCFailbackClassification.POST_CUTOVER_REVERSE_SYNC_REQUIRED:
            return {
                "cdc_session_id": self.cdc_session_id,
                "safe_auto_failback": False,
                "classification": classification.value if isinstance(classification, Enum) else classification,
                "status": "REVERSE_SYNC_REQUIRED",
                "action_required": "DRAIN_REVERSE_CDC_BEFORE_FAILBACK",
                "blockers": [],
                "current_role": self.current_role.value,
                "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        return {
            "cdc_session_id": self.cdc_session_id,
            "safe_auto_failback": True,
            "classification": classification.value if isinstance(classification, Enum) else classification,
            "status": "FAILBACK_ELIGIBLE",
            "blockers": [],
            "current_role": self.current_role.value,
            "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
