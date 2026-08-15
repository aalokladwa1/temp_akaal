"""
AKAAL Canonical End-to-End Migration Lifecycle Coordinator.
============================================================
Master lifecycle authority orchestrating the complete migration journey:
INITIAL LOAD -> CDC CAPTURE -> CONTINUOUS SYNC -> PRE-CUTOVER VALIDATION ->
RECONCILIATION -> CUTOVER READINESS -> SOURCE QUIESCENCE -> FINAL DRAIN ->
FINAL VALIDATION -> CUTOVER COMMIT -> TARGET PRIMARY -> POST-CUTOVER VALIDATION -> COMPLETED.
Enforces strict legal state transitions, rejects illegal jumps, and guarantees crash-recoverability.
"""

from typing import Dict, Any, List, Optional, Set
from enum import Enum
import uuid
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator

logger = logging.getLogger("akaal.cdc.lifecycle.coordinator")


class MigrationLifecycleState(str, Enum):
    """Canonical lifecycle states spanning initial load, CDC sync, cutover, and failback."""
    CREATED = "CREATED"
    CONFIGURING = "CONFIGURING"
    PREFLIGHT = "PREFLIGHT"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    SCHEMA_PREPARING = "SCHEMA_PREPARING"
    INITIAL_LOAD = "INITIAL_LOAD"
    INITIAL_VALIDATION = "INITIAL_VALIDATION"
    CDC_INITIALIZING = "CDC_INITIALIZING"
    CDC_ACTIVE = "CDC_ACTIVE"
    CDC_CATCHING_UP = "CDC_CATCHING_UP"
    CDC_SYNCHRONIZED = "CDC_SYNCHRONIZED"
    PRE_CUTOVER_VALIDATING = "PRE_CUTOVER_VALIDATING"
    RECONCILING = "RECONCILING"
    CUTOVER_BLOCKED = "CUTOVER_BLOCKED"
    CUTOVER_READY = "CUTOVER_READY"
    CUTOVER_APPROVAL_PENDING = "CUTOVER_APPROVAL_PENDING"
    SOURCE_QUIESCING = "SOURCE_QUIESCING"
    FINAL_DRAIN = "FINAL_DRAIN"
    FINAL_VALIDATION = "FINAL_VALIDATION"
    CUTOVER_COMMITTING = "CUTOVER_COMMITTING"
    TARGET_PRIMARY = "TARGET_PRIMARY"
    POST_CUTOVER_VALIDATING = "POST_CUTOVER_VALIDATING"
    COMPLETED = "COMPLETED"

    # Failure / Recovery / Maintenance states
    PAUSED = "PAUSED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILBACK_EVALUATING = "FAILBACK_EVALUATING"
    FAILBACK_READY = "FAILBACK_READY"
    FAILBACK_RUNNING = "FAILBACK_RUNNING"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class CDCMigrationLifecycleCoordinator:
    """
    Authoritative state machine orchestrating end-to-end migration lifecycle.
    Durable in CentralStateStore and restart-recoverable.
    """

    # Permitted legal forward and recovery state transitions
    LEGAL_TRANSITIONS: Dict[MigrationLifecycleState, Set[MigrationLifecycleState]] = {
        MigrationLifecycleState.CREATED: {MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.PREFLIGHT, MigrationLifecycleState.TERMINATED},
        MigrationLifecycleState.CONFIGURING: {MigrationLifecycleState.PREFLIGHT, MigrationLifecycleState.READY_FOR_APPROVAL, MigrationLifecycleState.FAILED, MigrationLifecycleState.TERMINATED},
        MigrationLifecycleState.PREFLIGHT: {MigrationLifecycleState.READY_FOR_APPROVAL, MigrationLifecycleState.APPROVED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.FAILED, MigrationLifecycleState.TERMINATED},
        MigrationLifecycleState.READY_FOR_APPROVAL: {MigrationLifecycleState.APPROVED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.FAILED, MigrationLifecycleState.TERMINATED},
        MigrationLifecycleState.APPROVED: {MigrationLifecycleState.SCHEMA_PREPARING, MigrationLifecycleState.INITIAL_LOAD, MigrationLifecycleState.FAILED, MigrationLifecycleState.PAUSED},
        MigrationLifecycleState.SCHEMA_PREPARING: {MigrationLifecycleState.INITIAL_LOAD, MigrationLifecycleState.FAILED, MigrationLifecycleState.PAUSED},
        MigrationLifecycleState.INITIAL_LOAD: {MigrationLifecycleState.INITIAL_VALIDATION, MigrationLifecycleState.CDC_INITIALIZING, MigrationLifecycleState.FAILED, MigrationLifecycleState.PAUSED},
        MigrationLifecycleState.INITIAL_VALIDATION: {MigrationLifecycleState.CDC_INITIALIZING, MigrationLifecycleState.CDC_ACTIVE, MigrationLifecycleState.FAILED, MigrationLifecycleState.PAUSED},
        MigrationLifecycleState.CDC_INITIALIZING: {MigrationLifecycleState.CDC_ACTIVE, MigrationLifecycleState.CDC_CATCHING_UP, MigrationLifecycleState.FAILED, MigrationLifecycleState.PAUSED},
        MigrationLifecycleState.CDC_ACTIVE: {MigrationLifecycleState.CDC_CATCHING_UP, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PRE_CUTOVER_VALIDATING, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CDC_CATCHING_UP: {MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.CDC_ACTIVE, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CDC_SYNCHRONIZED: {MigrationLifecycleState.PRE_CUTOVER_VALIDATING, MigrationLifecycleState.CUTOVER_APPROVAL_PENDING, MigrationLifecycleState.CUTOVER_READY, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.SOURCE_QUIESCING, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.PRE_CUTOVER_VALIDATING: {MigrationLifecycleState.RECONCILING, MigrationLifecycleState.CUTOVER_READY, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.RECONCILING: {MigrationLifecycleState.PRE_CUTOVER_VALIDATING, MigrationLifecycleState.CUTOVER_READY, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CUTOVER_BLOCKED: {MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PRE_CUTOVER_VALIDATING, MigrationLifecycleState.RECONCILING, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CUTOVER_APPROVAL_PENDING: {MigrationLifecycleState.CUTOVER_READY, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.SOURCE_QUIESCING, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CUTOVER_READY: {MigrationLifecycleState.SOURCE_QUIESCING, MigrationLifecycleState.FINAL_DRAIN, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.SOURCE_QUIESCING: {MigrationLifecycleState.FINAL_DRAIN, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.FINAL_DRAIN: {MigrationLifecycleState.FINAL_VALIDATION, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.FINAL_VALIDATION: {MigrationLifecycleState.CUTOVER_COMMITTING, MigrationLifecycleState.CUTOVER_BLOCKED, MigrationLifecycleState.RECONCILING, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.PAUSED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.CUTOVER_COMMITTING: {MigrationLifecycleState.TARGET_PRIMARY, MigrationLifecycleState.FAILBACK_EVALUATING, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.TARGET_PRIMARY: {MigrationLifecycleState.POST_CUTOVER_VALIDATING, MigrationLifecycleState.COMPLETED, MigrationLifecycleState.FAILBACK_EVALUATING, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.POST_CUTOVER_VALIDATING: {MigrationLifecycleState.COMPLETED, MigrationLifecycleState.FAILBACK_EVALUATING, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.PAUSED: {MigrationLifecycleState.CDC_ACTIVE, MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.CUTOVER_READY, MigrationLifecycleState.TERMINATED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.RECOVERY_REQUIRED: {MigrationLifecycleState.FAILBACK_EVALUATING, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.FAILBACK_EVALUATING: {MigrationLifecycleState.FAILBACK_READY, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.FAILBACK_READY: {MigrationLifecycleState.FAILBACK_RUNNING, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.FAILBACK_RUNNING: {MigrationLifecycleState.CDC_SYNCHRONIZED, MigrationLifecycleState.CDC_ACTIVE, MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED, MigrationLifecycleState.FAILED},
        MigrationLifecycleState.MANUAL_INTERVENTION_REQUIRED: {MigrationLifecycleState.FAILBACK_EVALUATING, MigrationLifecycleState.FAILED, MigrationLifecycleState.TERMINATED},
        MigrationLifecycleState.COMPLETED: set(),  # Terminal state
        MigrationLifecycleState.FAILED: set(),     # Terminal state
        MigrationLifecycleState.TERMINATED: set(), # Terminal state
    }

    def __init__(
        self,
        state_store: Optional[CentralStateStore] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
    ) -> None:
        self.state_store = state_store or CentralStateStore()
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def initialize_lifecycle(
        self,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        initial_state: MigrationLifecycleState = MigrationLifecycleState.CREATED,
    ) -> Dict[str, Any]:
        """Initializes a new durable lifecycle record."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        lifecycle_record = {
            "migration_id": migration_id,
            "job_id": job_id,
            "run_id": run_id,
            "cdc_session_id": cdc_session_id,
            "current_state": initial_state.value,
            "history": [
                {
                    "from_state": None,
                    "to_state": initial_state.value,
                    "timestamp": now_iso,
                    "reason": "Lifecycle initialized",
                }
            ],
            "validation_run_id": None,
            "cutover_plan_id": None,
            "recovery_plan_id": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        self.active_sessions[migration_id] = lifecycle_record
        self.state_store.set_state(
            f"migration_lifecycle_{migration_id}",
            lifecycle_record,
            category="migration_lifecycle",
        )
        logger.info(f"[LifecycleCoordinator] Initialized migration '{migration_id}' in state '{initial_state.value}'.")
        return lifecycle_record

    def transition_state(
        self,
        migration_id: str,
        target_state: MigrationLifecycleState,
        reason: str = "Automated progression",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transitions lifecycle state with strict legal state validation.
        Survives restarts and rejects illegal jumps or terminal state resurrection.
        """
        record = self.get_lifecycle(migration_id)
        if not record:
            raise ValueError(f"Migration '{migration_id}' lifecycle not found.")

        current_str = record["current_state"]
        current_enum = MigrationLifecycleState(current_str)

        if current_enum in (MigrationLifecycleState.COMPLETED, MigrationLifecycleState.FAILED, MigrationLifecycleState.TERMINATED):
            raise ValueError(f"Cannot transition from terminal state '{current_str}'. Terminal states are immutable.")

        legal_targets = self.LEGAL_TRANSITIONS.get(current_enum, set())
        if target_state not in legal_targets:
            raise ValueError(f"Illegal lifecycle transition: '{current_str}' -> '{target_state.value}' is not permitted.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record["current_state"] = target_state.value
        record["updated_at"] = now_iso
        record["history"].append({
            "from_state": current_str,
            "to_state": target_state.value,
            "timestamp": now_iso,
            "reason": reason,
            "metadata": metadata or {},
        })

        if metadata:
            if "validation_run_id" in metadata:
                record["validation_run_id"] = metadata["validation_run_id"]
            if "cutover_plan_id" in metadata:
                record["cutover_plan_id"] = metadata["cutover_plan_id"]
            if "recovery_plan_id" in metadata:
                record["recovery_plan_id"] = metadata["recovery_plan_id"]

        self.active_sessions[migration_id] = record
        self.state_store.set_state(
            f"migration_lifecycle_{migration_id}",
            record,
            category="migration_lifecycle",
        )
        logger.info(f"[LifecycleCoordinator] Migration '{migration_id}' transitioned: '{current_str}' -> '{target_state.value}' ({reason}).")
        return record

    def get_lifecycle(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves durable lifecycle state from memory or CentralStateStore."""
        if migration_id in self.active_sessions:
            return self.active_sessions[migration_id]

        stored = self.state_store.get_state(f"migration_lifecycle_{migration_id}", category="migration_lifecycle")
        if stored:
            self.active_sessions[migration_id] = stored
            return stored

        return None
