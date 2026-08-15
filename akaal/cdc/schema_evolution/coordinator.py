"""
AKAAL CDC Schema Evolution Orchestrator & Coordinator.
======================================================
Master orchestrator uniting DDL capture detection, canonical schema versioning,
compatibility analysis, schema evolution policy enforcement, transition barriers,
target DDL execution, post-apply verification, restart recovery, P3.4 cutover integration, and telemetry.
"""

from typing import Dict, Any, Optional, List
import uuid
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.cdc.schema_evolution.domain import (
    CDCSchemaVersion,
    CDCDDLEvent,
    DDLOperationType,
    SchemaCompatibilityClassification,
    SchemaEvolutionPolicyDecision,
    SchemaTransitionState,
    sanitize_ddl_statement,
)
from akaal.cdc.schema_evolution.detector import CDCDDLEngineDetector
from akaal.cdc.schema_evolution.evaluator import (
    CDCSchemaCompatibilityEvaluator,
    CDCSchemaEvolutionPolicyEngine,
)
from akaal.cdc.schema_evolution.barrier import CDCSchemaTransitionBarrier
from akaal.cdc.schema_evolution.transition_engine import CDCTargetSchemaTransitionEngine
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCSchemaEvolutionCoordinator:
    """Canonical Master Coordinator for CDC Live Schema Evolution."""

    def __init__(
        self,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()

        self.barrier_authority = CDCSchemaTransitionBarrier(state_store=self.state_store)
        self.transition_engine = CDCTargetSchemaTransitionEngine(
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
        )

        self.active_schema_versions: Dict[str, CDCSchemaVersion] = {}  # key: cdc_session_id:table_name
        self.version_history: Dict[str, List[CDCSchemaVersion]] = {}    # key: cdc_session_id:table_name
        self.pending_transitions: Dict[str, Dict[str, Any]] = {}       # key: transition_id
        self.session_fencing_epochs: Dict[str, int] = {}

    def get_or_register_initial_schema(
        self,
        identity: CDCEventIdentity,
        table_name: str,
        columns: List[Dict[str, Any]],
        primary_key_columns: Optional[List[str]] = None,
        source_engine: str = "POSTGRESQL",
        database_name: str = "db",
        schema_name: str = "public",
    ) -> CDCSchemaVersion:
        key = f"{identity.cdc_session_id}:{table_name}"
        if key not in self.active_schema_versions:
            ver = CDCSchemaVersion(
                identity=identity,
                source_engine=source_engine,
                database_name=database_name,
                schema_name=schema_name,
                table_name=table_name,
                columns=columns,
                primary_key_columns=primary_key_columns,
                version_number=1,
            )
            self.active_schema_versions[key] = ver
            self.version_history[key] = [ver]
            self.state_store.set_state(f"schema_ver_{key}_{ver.schema_version_id}", ver.to_dict(), category="schema_version")
        return self.active_schema_versions[key]

    def process_detected_ddl(
        self,
        identity: CDCEventIdentity,
        source_position: CDCSourcePosition,
        raw_statement_or_payload: Any,
        table_name: str,
        fencing_epoch: int,
        allow_auto_ddl: bool = True,
    ) -> Dict[str, Any]:
        key = f"{identity.cdc_session_id}:{table_name}"
        current_version = self.active_schema_versions.get(key)
        if not current_version:
            raise ValueError(f"No registered baseline schema version for session '{identity.cdc_session_id}' table '{table_name}'.")

        self.session_fencing_epochs[identity.cdc_session_id] = fencing_epoch

        # 1. Parse DDL & Build Proposed Version
        ddl_event = CDCDDLEngineDetector.detect_and_parse_ddl(
            identity=identity,
            source_engine=current_version.source_engine,
            source_position=source_position,
            raw_statement_or_payload=raw_statement_or_payload,
            current_schema_version=current_version,
        )

        # 2. Evaluate Compatibility & Policy
        proposed_version = CDCSchemaVersion.from_dict(
            self.state_store.get_state(f"schema_ver_{key}_{ddl_event.proposed_schema_version_id}", category="schema_version")
            or CDCDDLEngineDetector._build_proposed_schema_version(
                current_version, ddl_event.canonical_operation, ddl_event.operation_metadata
            ).to_dict()
        )

        compat = CDCSchemaCompatibilityEvaluator.evaluate_compatibility(current_version, proposed_version, ddl_event)
        ddl_event.compatibility = compat
        policy = CDCSchemaEvolutionPolicyEngine.determine_policy(compat, allow_auto_ddl=allow_auto_ddl)

        transition_id = f"trans-{identity.cdc_session_id}-{ddl_event.ddl_event_id}"

        # 3. Establish Barrier if required
        barrier_info = None
        if policy in {SchemaEvolutionPolicyDecision.PAUSES_AND_APPLIES, SchemaEvolutionPolicyDecision.REQUIRES_APPROVAL, SchemaEvolutionPolicyDecision.REQUIRES_TRANSFORMATION}:
            barrier_info = self.barrier_authority.establish_barrier(identity, table_name, ddl_event, fencing_epoch)

        transition_record = {
            "transition_id": transition_id,
            "identity": identity.to_dict(),
            "table_name": table_name,
            "ddl_event": ddl_event.to_dict(),
            "old_schema_version": current_version.to_dict(),
            "proposed_schema_version": proposed_version.to_dict(),
            "compatibility": compat.value,
            "policy_decision": policy.value,
            "barrier_id": barrier_info["barrier_id"] if barrier_info else None,
            "fencing_epoch": fencing_epoch,
            "state": SchemaTransitionState.AWAITING_APPROVAL.value if policy == SchemaEvolutionPolicyDecision.REQUIRES_APPROVAL else SchemaTransitionState.BARRIER_ESTABLISHED.value,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        self.pending_transitions[transition_id] = transition_record
        self.state_store.set_state(f"schema_pending_trans_{transition_id}", transition_record, category="schema_transition")
        self._publish_schema_telemetry(identity.cdc_session_id, transition_record)

        return transition_record

    def approve_schema_transition(
        self,
        transition_id: str,
        approved_by: str,
        approval_token: str,
    ) -> Dict[str, Any]:
        trans = self.pending_transitions.get(transition_id) or self.state_store.get_state(f"schema_pending_trans_{transition_id}", category="schema_transition")
        if not trans:
            raise ValueError(f"No pending schema transition with ID '{transition_id}'.")

        current_state = trans.get("state")
        if current_state in {SchemaTransitionState.COMPLETED.value, SchemaTransitionState.FAILED.value, "REJECTED"}:
            raise ValueError(f"Cannot approve transition in state '{current_state}'.")

        identity = CDCEventIdentity.from_dict(trans["identity"])
        app_rec = self.transition_engine.record_schema_approval(
            migration_id=identity.migration_id,
            job_id=identity.job_id,
            run_id=identity.run_id,
            cdc_session_id=identity.cdc_session_id,
            transition_id=transition_id,
            approved_by=approved_by,
            approval_token=approval_token,
            old_schema_version_id=trans["old_schema_version"]["schema_version_id"],
            new_schema_version_id=trans["proposed_schema_version"]["schema_version_id"],
        )
        trans["state"] = SchemaTransitionState.TARGET_DDL_STARTED.value
        trans["approval"] = app_rec
        self.pending_transitions[transition_id] = trans
        self.state_store.set_state(f"schema_pending_trans_{transition_id}", trans, category="schema_transition")
        return trans

    def apply_schema_transition(self, transition_id: str) -> Dict[str, Any]:
        trans = self.pending_transitions.get(transition_id) or self.state_store.get_state(f"schema_pending_trans_{transition_id}", category="schema_transition")
        if not trans:
            raise ValueError(f"No pending schema transition with ID '{transition_id}'.")

        identity = CDCEventIdentity.from_dict(trans["identity"])
        ddl_evt = CDCDDLEvent.from_dict(trans["ddl_event"])
        proposed_ver = CDCSchemaVersion.from_dict(trans["proposed_schema_version"])
        epoch = trans["fencing_epoch"]
        table_name = trans["table_name"]

        requires_app = trans["policy_decision"] == SchemaEvolutionPolicyDecision.REQUIRES_APPROVAL.value

        # Execute Target Transition
        exec_res = self.transition_engine.execute_target_transition(
            identity=identity,
            transition_id=transition_id,
            ddl_event=ddl_evt,
            proposed_schema=proposed_ver,
            fencing_epoch=epoch,
            requires_approval=requires_app,
        )

        # Release Barrier with Monotonic Fencing Epoch Validation
        if trans.get("barrier_id"):
            self.barrier_authority.release_barrier(
                cdc_session_id=identity.cdc_session_id,
                table_name=table_name,
                verified_schema_version_id=proposed_ver.schema_version_id,
                fencing_epoch=epoch,
                recovery_coordinator=self.recovery_coordinator,
                migration_id=identity.migration_id,
            )

        # Activate New Schema Version
        key = f"{identity.cdc_session_id}:{table_name}"
        self.active_schema_versions[key] = proposed_ver
        if key not in self.version_history:
            self.version_history[key] = []
        self.version_history[key].append(proposed_ver)

        trans["state"] = SchemaTransitionState.COMPLETED.value
        trans["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.state_store.set_state(f"schema_ver_{key}_{proposed_ver.schema_version_id}", proposed_ver.to_dict(), category="schema_version")
        self.state_store.set_state(f"schema_pending_trans_{transition_id}", trans, category="schema_transition")

        self._publish_schema_telemetry(identity.cdc_session_id, trans)
        return trans

    def recover_schema_transition(self, cdc_session_id: str, transition_id: str) -> Dict[str, Any]:
        persisted = self.state_store.get_state(f"schema_pending_trans_{transition_id}", category="schema_transition")
        if not persisted:
            raise ValueError(f"No persisted schema transition found for session '{cdc_session_id}' transition '{transition_id}'.")

        if persisted["identity"]["cdc_session_id"] != cdc_session_id:
            raise ValueError(f"Session identity mismatch during schema transition recovery. Expected '{cdc_session_id}', got '{persisted['identity']['cdc_session_id']}'.")

        self.pending_transitions[transition_id] = persisted
        return persisted

    def has_unresolved_schema_transition(self, cdc_session_id: str) -> bool:
        for trans in self.pending_transitions.values():
            if trans["identity"]["cdc_session_id"] == cdc_session_id and trans["state"] not in {SchemaTransitionState.COMPLETED.value, SchemaTransitionState.FAILED.value}:
                return True
        return False

    def _publish_schema_telemetry(self, cdc_session_id: str, transition_record: Dict[str, Any]) -> None:
        telemetry = {
            "cdc_session_id": cdc_session_id,
            "transition_id": transition_record["transition_id"],
            "state": transition_record["state"],
            "table_name": transition_record["table_name"],
            "canonical_operation": transition_record["ddl_event"]["canonical_operation"],
            "compatibility": transition_record["compatibility"],
            "policy_decision": transition_record["policy_decision"],
            "sanitized_ddl": transition_record["ddl_event"]["raw_ddl_statement"],
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.state_store.set_state(f"schema_telemetry_{cdc_session_id}", telemetry, category="schema_telemetry")
