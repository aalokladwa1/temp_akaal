"""
AKAAL CDC Multi-Master Conflict Detector Engine.
=================================================
Identifies true concurrent multi-master conflicts between peer replication streams by querying P3.7 CDCCausalityGraphEngine.
Differentiates causally ordered transactions, duplicate replays, and echo events from true non-causal entity conflicts.
"""

import uuid
import logging
import threading
import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from akaal.cdc.domain.events import CDCTransaction, CDCEventIdentity, CDCOperationType
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.multi_master.domain import (
    CDCConflictRecord,
    CDCConflictType,
    CDCConflictState,
)
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.cdc.multi_master.conflict_detector")


class CDCConflictDetector:
    """
    Backend-authoritative multi-master conflict detector.
    Integrates with P3.7 CDCCausalityGraphEngine to evaluate dependency edges and concurrency.
    """

    def __init__(
        self,
        topology_id: str,
        causality_graph: CDCCausalityGraphEngine,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.topology_id = topology_id
        self.causality_graph = causality_graph
        self.state_store = state_store or CentralStateStore()
        self._lock = threading.RLock()

        self.conflicts: Dict[str, CDCConflictRecord] = {}
        self._load_persisted_conflicts()

    def _get_conflict_state_key(self, conflict_id: str) -> str:
        return f"cdc_conflict_{self.topology_id}_{conflict_id}"

    def _load_persisted_conflicts(self) -> None:
        """Restores persisted conflict records from CentralStateStore on engine start."""
        if not self.state_store:
            return
        with self._lock:
            try:
                records_dict = self.state_store.get_state(f"cdc_conflict_records_{self.topology_id}", category="conflict_detector")
                if records_dict and isinstance(records_dict, dict):
                    for cid, cdict in records_dict.items():
                        self.conflicts[cid] = CDCConflictRecord.from_dict(cdict)
                    logger.info(f"[ConflictDetector] Restored {len(self.conflicts)} conflicts for topology '{self.topology_id}'.")
            except Exception as exc:
                fail = CDCFailure(
                    failure_type=CDCFailureType.CONFLICT_STATE_CORRUPTION,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[CONFLICT STATE CORRUPTION] Failed to restore conflict records: {exc}",
                    migration_id="mig-unknown",
                    job_id="job-unknown",
                    run_id="run-unknown",
                    cdc_session_id="sess-unknown",
                )
                raise CDCExecutionError(fail)

    def _persist_conflicts(self) -> None:
        """Persists conflict record dictionary into CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            data = {cid: c.to_dict() for cid, c in self.conflicts.items()}
            self.state_store.set_state(f"cdc_conflict_records_{self.topology_id}", data, category="conflict_detector")

    def detect_conflict(
        self,
        identity: CDCEventIdentity,
        tx_a: CDCTransaction,
        tx_b: CDCTransaction,
    ) -> Optional[CDCConflictRecord]:
        """
        Evaluates whether transactions tx_a (from Node A) and tx_b (from Node B) constitute a multi-master conflict.
        Returns CDCConflictRecord if a true non-causal conflict exists, or None if causally ordered/non-conflicting.
        """
        with self._lock:
            # 1. Identity binding check
            if (
                tx_a.identity.migration_id != identity.migration_id
                or tx_b.identity.migration_id != identity.migration_id
            ):
                fail = CDCFailure(
                    failure_type=CDCFailureType.TOPOLOGY_IDENTITY_MISMATCH,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[IDENTITY MISMATCH] Transactions do not match topology migration '{identity.migration_id}'.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            # 2. Extract modified entity keys for both transactions
            keys_a = self.causality_graph.extract_entity_keys(tx_a)
            keys_b = self.causality_graph.extract_entity_keys(tx_b)
            common_keys = keys_a.intersection(keys_b)

            if not common_keys:
                # No shared entities -> Independent transactions, no conflict
                return None

            # 3. Extract common entity table and key
            tbl, key = next(iter(common_keys))

            # 4. Check P3.7 Causality Graph for completed dependency precedence or entity history
            # If tx_a occurred before tx_b on the same entity and tx_a is completed, tx_b is causally ordered AFTER tx_a.
            ent_hist = self.causality_graph.entity_history.get(f"{tbl}:{key}", [])
            if tx_a.tx_id in ent_hist and tx_b.tx_id in ent_hist:
                idx_a = ent_hist.index(tx_a.tx_id)
                idx_b = ent_hist.index(tx_b.tx_id)
                if idx_a < idx_b and tx_a.tx_id in self.causality_graph.completed_txs:
                    return None
                if idx_b < idx_a and tx_b.tx_id in self.causality_graph.completed_txs:
                    return None

            preds_b = self.causality_graph.predecessors.get(tx_b.tx_id, set())
            preds_a = self.causality_graph.predecessors.get(tx_a.tx_id, set())

            if (tx_a.tx_id in preds_b and tx_a.tx_id in self.causality_graph.completed_txs) or (tx_b.tx_id in preds_a and tx_b.tx_id in self.causality_graph.completed_txs):
                # Causally ordered mutation (predecessor already completed) -> NOT a concurrent multi-master conflict
                return None

            # 5. Same transaction replay or duplicate replay check
            if tx_a.tx_id == tx_b.tx_id:
                return None

            # 6. Determine operation types for common entity
            op_a = tx_a.events[0].operation if tx_a.events else CDCOperationType.UPDATE
            op_b = tx_b.events[0].operation if tx_b.events else CDCOperationType.UPDATE

            # 6. Classify conflict type
            ctype: Optional[CDCConflictType] = None
            if op_a == CDCOperationType.UPDATE and op_b == CDCOperationType.UPDATE:
                ctype = CDCConflictType.UPDATE_UPDATE
            elif op_a == CDCOperationType.UPDATE and op_b == CDCOperationType.DELETE:
                ctype = CDCConflictType.UPDATE_DELETE
            elif op_a == CDCOperationType.DELETE and op_b == CDCOperationType.UPDATE:
                ctype = CDCConflictType.DELETE_UPDATE
            elif op_a == CDCOperationType.INSERT and op_b == CDCOperationType.INSERT:
                ctype = CDCConflictType.INSERT_INSERT
            elif op_a == CDCOperationType.DELETE and op_b == CDCOperationType.DELETE:
                # Both deleted same record -> Idempotent non-conflict
                return None
            elif op_a == CDCOperationType.INSERT and op_b == CDCOperationType.UPDATE:
                ctype = CDCConflictType.INSERT_UPDATE
            elif op_a == CDCOperationType.UPDATE and op_b == CDCOperationType.INSERT:
                ctype = CDCConflictType.UPDATE_INSERT
            else:
                ctype = CDCConflictType.UPDATE_UPDATE

            # 7. Create identity-bound conflict record
            conflict_id = f"conf-{uuid.uuid4().hex[:8]}"
            record = CDCConflictRecord(
                conflict_id=conflict_id,
                topology_id=self.topology_id,
                migration_id=identity.migration_id,
                job_id=identity.job_id,
                run_id=identity.run_id,
                entity_table=tbl,
                entity_key=key,
                source_a_tx_id=tx_a.tx_id,
                source_b_tx_id=tx_b.tx_id,
                source_a_position=str(tx_a.commit_position),
                source_b_position=str(tx_b.commit_position),
                conflict_type=ctype,
                conflict_state=CDCConflictState.DETECTED,
                causal_evidence_ref=f"causal_graph_{self.causality_graph.cdc_session_id}",
            )

            self.conflicts[conflict_id] = record
            self._persist_conflicts()
            logger.warning(
                f"[ConflictDetector] Multi-master conflict '{conflict_id}' ({ctype.value}) "
                f"detected for entity '{tbl}:{key}' between tx_a='{tx_a.tx_id}' and tx_b='{tx_b.tx_id}'."
            )
            return record

    def get_conflict(self, conflict_id: str) -> Optional[CDCConflictRecord]:
        """Returns conflict record by ID."""
        with self._lock:
            return self.conflicts.get(conflict_id)

    def get_unresolved_conflicts(self) -> List[CDCConflictRecord]:
        """Returns list of active/unresolved conflict records."""
        with self._lock:
            return [
                c for c in self.conflicts.values()
                if c.conflict_state not in (CDCConflictState.RESOLVED, CDCConflictState.RELEASED)
            ]

    def update_conflict_state(self, conflict_id: str, new_state: CDCConflictState) -> CDCConflictRecord:
        """Updates lifecycle state of conflict record."""
        with self._lock:
            record = self.conflicts.get(conflict_id)
            if not record:
                fail = CDCFailure(
                    failure_type=CDCFailureType.CONFLICT_STATE_CORRUPTION,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[CONFLICT NOT FOUND] Conflict ID '{conflict_id}' does not exist.",
                    migration_id="mig-unknown",
                    job_id="job-unknown",
                    run_id="run-unknown",
                    cdc_session_id="sess-unknown",
                )
                raise CDCExecutionError(fail)

            record.conflict_state = new_state
            self._persist_conflicts()
            return record
