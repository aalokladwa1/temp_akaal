"""
AKAAL CDC Multi-Master Deterministic Conflict Resolver.
=========================================================
Evaluates and applies deterministic conflict resolution policies (SOURCE_A_WINS, SOURCE_B_WINS,
DESIGNATED_PRIMARY_WINS, LATEST_VERSION_WINS, MANUAL_GOVERNANCE_REQUIRED).
Enforces monotonic worker fencing token validation via RecoveryCoordinator.
"""

import uuid
import logging
import threading
import datetime
from typing import Dict, Any, List, Optional

from akaal.cdc.domain.events import CDCTransaction, CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.multi_master.domain import (
    CDCConflictRecord,
    CDCConflictType,
    CDCConflictState,
    CDCConflictResolutionPolicy,
    CDCConflictResolutionDecision,
)
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.cdc.multi_master.resolver")


class CDCConflictResolver:
    """
    Backend-authoritative conflict resolution engine.
    Evaluates policy, validates fencing epoch, and creates durable CDCConflictResolutionDecision records.
    """

    def __init__(

        self,
        topology_id: str,
        conflict_detector: CDCConflictDetector,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
        designated_primary_database_id: Optional[str] = None,
    ) -> None:
        self.topology_id = topology_id
        self.conflict_detector = conflict_detector
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self.designated_primary_database_id = designated_primary_database_id
        self._lock = threading.RLock()

        self.decisions: Dict[str, CDCConflictResolutionDecision] = {}
        self._load_persisted_decisions()

    def _load_persisted_decisions(self) -> None:
        """Restores persisted resolution decisions from CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            try:
                dec_dict = self.state_store.get_state(f"cdc_conflict_decisions_{self.topology_id}", category="conflict_resolver")
                if dec_dict and isinstance(dec_dict, dict):
                    for did, ddict in dec_dict.items():
                        self.decisions[did] = CDCConflictResolutionDecision.from_dict(ddict)
                    logger.info(f"[ConflictResolver] Restored {len(self.decisions)} decisions for topology '{self.topology_id}'.")
            except Exception as exc:
                fail = CDCFailure(
                    failure_type=CDCFailureType.CONFLICT_STATE_CORRUPTION,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[DECISION STATE CORRUPTION] Failed to restore resolution decisions: {exc}",
                    migration_id="mig-unknown",
                    job_id="job-unknown",
                    run_id="run-unknown",
                    cdc_session_id="sess-unknown",
                )
                raise CDCExecutionError(fail)

    def _persist_decisions(self) -> None:
        """Persists decision dictionary into CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            data = {did: d.to_dict() for did, d in self.decisions.items()}
            self.state_store.set_state(f"cdc_conflict_decisions_{self.topology_id}", data, category="conflict_resolver")

    def resolve_conflict(
        self,
        identity: CDCEventIdentity,
        conflict_id: str,
        policy: CDCConflictResolutionPolicy,
        fencing_epoch: int,
        manual_winner: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> CDCConflictResolutionDecision:
        """
        Evaluates resolution policy for conflict_id and produces identity-bound CDCConflictResolutionDecision.
        Validates fencing epoch via RecoveryCoordinator.
        """
        with self._lock:
            # 1. Monotonic Fencing Token Validation
            if not self.recovery_coordinator.validate_fencing_token(identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_CONFLICT_RESOLVER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE RESOLVER] Stale fencing epoch {fencing_epoch} rejected for conflict '{conflict_id}'.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            # 2. Fetch conflict record
            record = self.conflict_detector.get_conflict(conflict_id)
            if not record:
                fail = CDCFailure(
                    failure_type=CDCFailureType.CONFLICT_STATE_CORRUPTION,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[CONFLICT NOT FOUND] Conflict record '{conflict_id}' does not exist.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            # 3. Idempotent duplicate check
            for existing_dec in self.decisions.values():
                if existing_dec.conflict_id == conflict_id:
                    if existing_dec.policy == policy and (manual_winner is None or existing_dec.selected_winner == manual_winner):
                        logger.info(f"[ConflictResolver] Returning existing idempotent decision for conflict '{conflict_id}'.")
                        return existing_dec

            # 4. Policy evaluation logic
            winner: str = "SOURCE_A"
            decision_reason: str = reason or f"Resolved via policy {policy.value}"

            if policy == CDCConflictResolutionPolicy.SOURCE_A_WINS:
                winner = "SOURCE_A"

            elif policy == CDCConflictResolutionPolicy.SOURCE_B_WINS:
                winner = "SOURCE_B"

            elif policy == CDCConflictResolutionPolicy.DESIGNATED_PRIMARY_WINS:
                if not self.designated_primary_database_id:
                    # Designated primary UNKNOWN -> Fail closed into MANUAL_GOVERNANCE_REQUIRED
                    policy = CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED
                    winner = "MANUAL_GOVERNANCE"
                    decision_reason = "Designated primary unknown; falling back to manual governance."
                else:
                    winner = "SOURCE_A"  # Primary peer winner

            elif policy == CDCConflictResolutionPolicy.LATEST_VERSION_WINS:
                # Compare position values (LSN/SCN coordinates)
                pos_a = record.source_a_position
                pos_b = record.source_b_position
                if pos_a and pos_b and pos_a != pos_b:
                    winner = "SOURCE_A" if pos_a > pos_b else "SOURCE_B"
                else:
                    # Indeterminate version comparison -> Fail closed into MANUAL_GOVERNANCE_REQUIRED
                    policy = CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED
                    winner = "MANUAL_GOVERNANCE"
                    decision_reason = "LATEST_VERSION position coordinates inconclusive; falling back to manual governance."

            elif policy == CDCConflictResolutionPolicy.MANUAL_GOVERNANCE_REQUIRED:
                if manual_winner in ("SOURCE_A", "SOURCE_B"):
                    winner = manual_winner
                    decision_reason = reason or f"Manual operator governance decision: {manual_winner} selected."
                else:
                    # Require operator review
                    self.conflict_detector.update_conflict_state(conflict_id, CDCConflictState.MANUAL_REVIEW_REQUIRED)
                    fail = CDCFailure(
                        failure_type=CDCFailureType.CONFLICT_RESOLUTION_REJECTED,
                        category=CDCFailureCategory.BLOCKING,
                        message=f"[MANUAL GOVERNANCE REQUIRED] Conflict '{conflict_id}' requires explicit operator winner selection.",
                        migration_id=identity.migration_id,
                        job_id=identity.job_id,
                        run_id=identity.run_id,
                        cdc_session_id=identity.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)

            # 5. Create resolution decision
            res_id = f"dec-{uuid.uuid4().hex[:8]}"
            decision = CDCConflictResolutionDecision(
                resolution_id=res_id,
                conflict_id=conflict_id,
                topology_id=self.topology_id,
                migration_id=identity.migration_id,
                run_id=identity.run_id,
                policy=policy,
                selected_winner=winner,
                decision_reason=decision_reason,
                decision_evidence={
                    "entity_table": record.entity_table,
                    "entity_key": record.entity_key,
                    "source_a_tx_id": record.source_a_tx_id,
                    "source_b_tx_id": record.source_b_tx_id,
                },
                fencing_epoch=fencing_epoch,
                decision_state="APPROVED",
            )

            self.decisions[res_id] = decision
            self.conflict_detector.update_conflict_state(conflict_id, CDCConflictState.RESOLVED)
            self._persist_decisions()

            logger.info(f"[ConflictResolver] Resolved conflict '{conflict_id}' using policy '{policy.value}'. Winner: '{winner}'.")
            return decision

    def get_decision(self, resolution_id: str) -> Optional[CDCConflictResolutionDecision]:
        """Returns resolution decision by ID."""
        with self._lock:
            return self.decisions.get(resolution_id)
