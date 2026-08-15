"""
AKAAL CDC Bidirectional Replication Topology Manager.
======================================================
Master orchestrator managing Node A <-> Node B dual-stream continuous CDC topology lifecycle.
Integrates loop filter, conflict detector, resolver, quarantine manager, and EngineGateway capabilities.
"""

import uuid
import logging
import threading
import datetime
from typing import Dict, Any, List, Optional, Tuple

from akaal.cdc.domain.events import CDCTransaction, CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.multi_master.domain import (
    CDCReplicationTopology,
    CDCReplicationTopologyState,
    CDCReplicationDirection,
    CDCDirectionState,
    CDCConflictRecord,
    CDCConflictResolutionPolicy,
    CDCConflictResolutionDecision,
    CDCQuarantineRecord,
)
from akaal.cdc.multi_master.loop_filter import CDCReplicationLoopFilter
from akaal.cdc.multi_master.conflict_detector import CDCConflictDetector
from akaal.cdc.multi_master.resolver import CDCConflictResolver
from akaal.cdc.multi_master.quarantine import CDCConflictQuarantineManager
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.cdc.multi_master.topology")


class CDCBirectionalTopologyManager:
    """
    Backend-authoritative master bidirectional topology manager.
    Coordinates Node A <-> Node B continuous replication, echo suppression, conflict resolution, and quarantine.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        source_a_database_id: str,
        source_b_database_id: str,
        topology_id: Optional[str] = None,
        causality_graph: Optional[CDCCausalityGraphEngine] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
        designated_primary_database_id: Optional[str] = None,
    ) -> None:
        self.identity = identity
        self.source_a_database_id = source_a_database_id
        self.source_b_database_id = source_b_database_id
        self.topology_id = topology_id or f"top-{uuid.uuid4().hex[:8]}"

        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()

        self.fencing_epoch = self.recovery_coordinator.active_epochs.get(self.identity.migration_id, 1)

        self.causality_graph = causality_graph or CDCCausalityGraphEngine(
            cdc_session_id=self.identity.cdc_session_id,
            state_store=self.state_store,
        )

        self.loop_filter_a_to_b = CDCReplicationLoopFilter(
            local_database_id=source_a_database_id,
            topology_id=self.topology_id,
            run_id=self.identity.run_id,
        )
        self.loop_filter_b_to_a = CDCReplicationLoopFilter(
            local_database_id=source_b_database_id,
            topology_id=self.topology_id,
            run_id=self.identity.run_id,
        )

        self.conflict_detector = CDCConflictDetector(
            topology_id=self.topology_id,
            causality_graph=self.causality_graph,
            state_store=self.state_store,
        )

        self.conflict_resolver = CDCConflictResolver(
            topology_id=self.topology_id,
            conflict_detector=self.conflict_detector,
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
            designated_primary_database_id=designated_primary_database_id,
        )

        self.quarantine_manager = CDCConflictQuarantineManager(
            topology_id=self.topology_id,
            recovery_coordinator=self.recovery_coordinator,
            state_store=self.state_store,
        )

        self._lock = threading.RLock()
        self.topology = self._initialize_topology(designated_primary_database_id)

    def _initialize_topology(self, designated_primary: Optional[str]) -> CDCReplicationTopology:
        """Initializes or restores CDCReplicationTopology model."""
        with self._lock:
            key = f"cdc_topology_{self.topology_id}"
            existing = self.state_store.get_state(key, category="multi_master_topology")
            if existing and isinstance(existing, dict):
                top = CDCReplicationTopology.from_dict(existing)
                logger.info(f"[TopologyManager] Restored topology '{self.topology_id}' in state '{top.state}'.")
                return top

            dir_a_b = CDCDirectionState(
                direction_id=f"{self.topology_id}_a_to_b",
                source_database_id=self.source_a_database_id,
                target_database_id=self.source_b_database_id,
                cdc_session_id=f"sess_{self.source_a_database_id}_to_{self.source_b_database_id}",
                fencing_epoch=self.fencing_epoch,
            )

            dir_b_a = CDCDirectionState(
                direction_id=f"{self.topology_id}_b_to_a",
                source_database_id=self.source_b_database_id,
                target_database_id=self.source_a_database_id,
                cdc_session_id=f"sess_{self.source_b_database_id}_to_{self.source_a_database_id}",
                fencing_epoch=self.fencing_epoch,
            )

            top = CDCReplicationTopology(
                topology_id=self.topology_id,
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                source_a_database_id=self.source_a_database_id,
                source_b_database_id=self.source_b_database_id,
                cdc_session_a_to_b=dir_a_b.cdc_session_id,
                cdc_session_b_to_a=dir_b_a.cdc_session_id,
                state=CDCReplicationTopologyState.ACTIVE,
                direction_a_to_b=dir_a_b,
                direction_b_to_a=dir_b_a,
                designated_primary_database_id=designated_primary,
                fencing_epoch=self.fencing_epoch,
            )
            self._persist_topology(top)
            return top

    def _persist_topology(self, topology: CDCReplicationTopology) -> None:
        """Persists topology model in CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            key = f"cdc_topology_{self.topology_id}"
            topology.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.state_store.set_state(key, topology.to_dict(), category="multi_master_topology")

    def process_incoming_transaction(
        self,
        transaction: CDCTransaction,
        direction: CDCReplicationDirection,
        fencing_epoch: int,
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates incoming transaction for loop filtering, conflict detection, quarantine, and replay eligibility.
        Returns (is_ready_to_apply, reason_message).
        """
        with self._lock:
            # 1. Fencing validation
            if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE WORKER] Stale fencing epoch {fencing_epoch} rejected.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            # 2. Topology state check
            if self.topology.state in (CDCReplicationTopologyState.PAUSED, CDCReplicationTopologyState.FAILED):
                return False, f"Topology is in '{self.topology.state.value}' state"

            # 3. Echo / Loop Filter Check
            loop_filter = self.loop_filter_a_to_b if direction == CDCReplicationDirection.A_TO_B else self.loop_filter_b_to_a
            if loop_filter.should_suppress_transaction(transaction, self.identity):
                return False, "Echo event suppressed by loop filter"

            # 4. Check if entity key is currently quarantined
            keys = self.causality_graph.extract_entity_keys(transaction)
            for tbl, key in keys:
                if self.quarantine_manager.is_entity_quarantined(tbl, key):
                    return False, f"Entity '{tbl}:{key}' is quarantined due to unresolved multi-master conflict"

            # 5. Add to Causality DAG
            self.causality_graph.add_transaction(transaction)

            # 6. Attach origin provenance for downstream apply tracking
            loop_filter.attach_origin_provenance(transaction, direction.value)
            return True, "READY"

    def pause_topology(self, fencing_epoch: int) -> CDCReplicationTopology:
        """Pauses bidirectional replication topology."""
        with self._lock:
            if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE WORKER] Stale epoch {fencing_epoch} rejected.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            self.topology.state = CDCReplicationTopologyState.PAUSED
            self._persist_topology(self.topology)
            logger.info(f"[TopologyManager] Topology '{self.topology_id}' paused.")
            return self.topology

    def resume_topology(self, fencing_epoch: int) -> CDCReplicationTopology:
        """Resumes bidirectional replication topology."""
        with self._lock:
            if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE WORKER] Stale epoch {fencing_epoch} rejected.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            self.topology.state = CDCReplicationTopologyState.ACTIVE
            self._persist_topology(self.topology)
            logger.info(f"[TopologyManager] Topology '{self.topology_id}' resumed.")
            return self.topology

    def resolve_conflict(
        self,
        conflict_id: str,
        policy: Any,
        fencing_epoch: int = 1,
        winner_source_id: Optional[str] = None,
        operator_id: str = "operator",
    ) -> CDCConflictResolutionDecision:
        """Resolves conflict via underlying conflict_resolver."""
        pol = CDCConflictResolutionPolicy(policy) if isinstance(policy, str) else policy
        return self.conflict_resolver.resolve_conflict(
            identity=self.identity,
            conflict_id=conflict_id,
            policy=pol,
            fencing_epoch=fencing_epoch,
            manual_winner=winner_source_id,
            reason=f"Resolved by {operator_id}",
        )

    def is_cutover_eligible(self) -> bool:
        """
        Cutover readiness validation gate.
        Returns False if any unresolved multi-master conflict or active quarantine exists.
        """
        with self._lock:
            unresolved = self.conflict_detector.get_unresolved_conflicts()
            active_q = self.quarantine_manager.get_active_quarantines()
            if unresolved or active_q:
                logger.warning(
                    f"[TopologyManager] Cutover gate blocked: {len(unresolved)} unresolved conflicts, "
                    f"{len(active_q)} active entity quarantines."
                )
                return False
            return True

    def get_telemetry(self) -> Dict[str, Any]:
        """Exposes backend-authoritative monitoring telemetry."""
        with self._lock:
            unresolved = self.conflict_detector.get_unresolved_conflicts()
            active_q = self.quarantine_manager.get_active_quarantines()
            return {
                "topology_id": self.topology_id,
                "topology_state": self.topology.state.value,
                "direction_a_to_b_state": self.topology.direction_a_to_b.to_dict() if self.topology.direction_a_to_b else None,
                "direction_b_to_a_state": self.topology.direction_b_to_a.to_dict() if self.topology.direction_b_to_a else None,
                "conflicts_detected_total": len(self.conflict_detector.conflicts),
                "conflicts_unresolved": len(unresolved),
                "quarantined_entities_count": len(active_q),
                "echo_events_suppressed_a_to_b": self.loop_filter_a_to_b.echo_events_suppressed_count,
                "echo_events_suppressed_b_to_a": self.loop_filter_b_to_a.echo_events_suppressed_count,
                "cutover_eligible": self.is_cutover_eligible(),
                "designated_primary": self.topology.designated_primary_database_id,
                "fencing_epoch": self.topology.fencing_epoch,
            }
