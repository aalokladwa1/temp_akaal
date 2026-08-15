"""
AKAAL CDC Durable Cutover Plan, Quiescence Contract & Readiness Engine.
========================================================================
Defines identity-bound durable cutover plans, idempotent phase tracking, source quiescence contracts,
approval integration, and backend-authoritative cutover readiness evaluation.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.cdc.domain.durability import CDCCheckpoint

logger = logging.getLogger(__name__)


class CutoverPhase(str, Enum):
    """Durable cutover phase progress tracking for idempotent execution."""
    NOT_STARTED = "NOT_STARTED"
    PRECHECK_COMPLETE = "PRECHECK_COMPLETE"
    SOURCE_QUIESCED = "SOURCE_QUIESCED"
    FINAL_BOUNDARY_CAPTURED = "FINAL_BOUNDARY_CAPTURED"
    FINAL_DRAIN_COMPLETE = "FINAL_DRAIN_COMPLETE"
    FINAL_VALIDATION_COMPLETE = "FINAL_VALIDATION_COMPLETE"
    APPROVAL_COMPLETE = "APPROVAL_COMPLETE"
    CUTOVER_COMMITTED = "CUTOVER_COMMITTED"
    CUTOVER_COMPLETED = "CUTOVER_COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class SourceQuiescenceMode(str, Enum):
    """Source application quiescence verification contract."""
    MANUAL_EXTERNAL_QUIESCENCE = "MANUAL_EXTERNAL_QUIESCENCE"
    ENGINE_FENCED_QUIESCENCE = "ENGINE_FENCED_QUIESCENCE"


class CDCSourceQuiescenceContract:
    """Contract verifying source database write quiescence before final CDC drain."""

    def __init__(
        self,
        cdc_session_id: str,
        mode: SourceQuiescenceMode = SourceQuiescenceMode.MANUAL_EXTERNAL_QUIESCENCE,
        verified_by: str = "operator",
        final_expected_lsn: Optional[CDCSourcePosition] = None,
    ) -> None:
        self.cdc_session_id = cdc_session_id
        self.mode = mode
        self.verified_by = verified_by
        self.final_expected_lsn = final_expected_lsn
        self.is_quiesced = False
        self.quiesced_at: Optional[str] = None

    def mark_quiesced(self, final_lsn: CDCSourcePosition) -> None:
        self.final_expected_lsn = final_lsn
        self.is_quiesced = True
        self.quiesced_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdc_session_id": self.cdc_session_id,
            "mode": self.mode.value,
            "verified_by": self.verified_by,
            "final_expected_lsn": self.final_expected_lsn.to_dict() if self.final_expected_lsn else None,
            "is_quiesced": self.is_quiesced,
            "quiesced_at": self.quiesced_at,
        }


class CDCCutoverPlan:
    """Durable Cutover Plan bound to migration, job, run, and CDC session identity."""

    def __init__(
        self,
        identity: CDCEventIdentity,
        fencing_epoch: int,
        requested_by: str = "operator",
        cutover_mode: str = "GOVERNED_MANUAL",
        plan_id: Optional[str] = None,
    ) -> None:
        self.plan_id = plan_id or f"plan-cutover-{uuid.uuid4().hex[:8]}"
        self.identity = identity
        self.fencing_epoch = fencing_epoch
        self.requested_by = requested_by
        self.cutover_mode = cutover_mode
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.current_phase = CutoverPhase.NOT_STARTED
        self.quiescence_contract: Optional[CDCSourceQuiescenceContract] = None
        self.final_source_position: Optional[CDCSourcePosition] = None
        self.final_applied_position: Optional[CDCSourcePosition] = None
        self.final_checkpoint: Optional[CDCCheckpoint] = None

        self.approval_reference: Optional[Dict[str, Any]] = None
        self.validation_reference: Optional[Dict[str, Any]] = None
        self.is_committed = False
        self.committed_at: Optional[str] = None

    def advance_phase(self, target_phase: CutoverPhase) -> None:
        logger.info(f"[CDCCutoverPlan] Plan '{self.plan_id}' advancing phase from '{self.current_phase.value}' to '{target_phase.value}'.")
        self.current_phase = target_phase
        if target_phase == CutoverPhase.CUTOVER_COMMITTED:
            self.is_committed = True
            self.committed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "identity": self.identity.to_dict(),
            "fencing_epoch": self.fencing_epoch,
            "requested_by": self.requested_by,
            "cutover_mode": self.cutover_mode,
            "created_at": self.created_at,
            "current_phase": self.current_phase.value,
            "quiescence_contract": self.quiescence_contract.to_dict() if self.quiescence_contract else None,
            "final_source_position": self.final_source_position.to_dict() if self.final_source_position else None,
            "final_applied_position": self.final_applied_position.to_dict() if self.final_applied_position else None,
            "final_checkpoint": self.final_checkpoint.to_dict() if self.final_checkpoint else None,
            "approval_reference": self.approval_reference,
            "validation_reference": self.validation_reference,
            "is_committed": self.is_committed,
            "committed_at": self.committed_at,
        }


class CDCCutoverReadinessEngine:
    """Backend-authoritative cutover readiness evaluator."""

    @classmethod
    def evaluate_readiness(
        cls,
        cdc_session_id: str,
        session_state: str,
        is_synchronized: bool,
        event_backlog: int,
        time_lag_ms: float,
        checkpoint_valid: bool,
        has_failed_transactions: bool,
        is_stale_worker: bool,
        validation_passed: bool = True,
        approval_granted: bool = True,
        max_allowed_backlog: int = 5,
        max_allowed_lag_ms: float = 2000.0,
    ) -> Dict[str, Any]:
        blocking_reasons: List[str] = []
        warnings: List[str] = []

        if session_state not in {"SYNCHRONIZED", "CUTOVER_PREPARING", "FINAL_DRAIN", "VALIDATING", "CUTOVER_READY"}:
            blocking_reasons.append(f"SESSION_NOT_SYNCHRONIZED (Current State: {session_state})")

        if not is_synchronized:
            blocking_reasons.append("CDC_NOT_SUSTAINED_SYNCHRONIZED")

        if event_backlog > max_allowed_backlog:
            blocking_reasons.append(f"BACKLOG_TOO_HIGH ({event_backlog} > {max_allowed_backlog})")
        elif event_backlog > 0:
            warnings.append(f"BACKLOG_NON_ZERO ({event_backlog} events buffered)")

        if time_lag_ms > max_allowed_lag_ms:
            blocking_reasons.append(f"TIME_LAG_TOO_HIGH ({time_lag_ms}ms > {max_allowed_lag_ms}ms)")

        if not checkpoint_valid:
            blocking_reasons.append("CHECKPOINT_INTEGRITY_INVALID")

        if has_failed_transactions:
            blocking_reasons.append("UNRESOLVED_TRANSACTION_FAILURES")

        if is_stale_worker:
            blocking_reasons.append("STALE_WORKER_FENCING_TOKEN")

        if not validation_passed:
            blocking_reasons.append("FINAL_VALIDATION_BLOCKER")

        if not approval_granted:
            blocking_reasons.append("GOVERNANCE_APPROVAL_MISSING")

        is_ready = (len(blocking_reasons) == 0)

        return {
            "cdc_session_id": cdc_session_id,
            "ready": is_ready,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
