"""
AKAAL CDC Failback Decision Engine & Primary Role Authority.
=============================================================
Manages primary role states (SOURCE_PRIMARY, CUTOVER_TRANSITION, TARGET_PRIMARY, FAILBACK_TRANSITION, UNKNOWN),
evaluates pre-cutover abort safety, and performs post-cutover failback eligibility checks.
Fails closed with MANUAL_INTERVENTION_REQUIRED when unsafe divergence is detected.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.sync.cutover_plan import CDCCutoverPlan, CutoverPhase

logger = logging.getLogger(__name__)


class PrimaryRoleState(str, Enum):
    """Authoritative primary database role tracking."""
    SOURCE_PRIMARY = "SOURCE_PRIMARY"
    CUTOVER_TRANSITION = "CUTOVER_TRANSITION"
    TARGET_PRIMARY = "TARGET_PRIMARY"
    FAILBACK_TRANSITION = "FAILBACK_TRANSITION"
    UNKNOWN = "UNKNOWN"


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
                "reason": "CUTOVER_ALREADY_COMMITTED",
                "action_required": "USE_POST_CUTOVER_FAILBACK",
            }
        return {
            "cdc_session_id": self.cdc_session_id,
            "can_abort": True,
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

        if not cutover_plan or not cutover_plan.is_committed:
            blockers.append("CUTOVER_NOT_COMMITTED")

        if target_received_post_cutover_writes and not reverse_cdc_available:
            blockers.append("POST_CUTOVER_TARGET_WRITES_WITHOUT_REVERSE_CDC")

        if target_received_post_cutover_writes and source_received_post_cutover_writes:
            blockers.append("SPLIT_BRAIN_BOTH_DATABASES_RECEIVED_WRITES")

        if self.current_role == PrimaryRoleState.UNKNOWN:
            blockers.append("UNKNOWN_AUTHORITATIVE_ROLE_STATE")

        if blockers:
            return {
                "cdc_session_id": self.cdc_session_id,
                "safe_auto_failback": False,
                "status": "MANUAL_INTERVENTION_REQUIRED",
                "blockers": blockers,
                "current_role": self.current_role.value,
                "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        return {
            "cdc_session_id": self.cdc_session_id,
            "safe_auto_failback": True,
            "status": "FAILBACK_ELIGIBLE",
            "blockers": [],
            "current_role": self.current_role.value,
            "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
