"""
AKAAL CDC Multi-Master Conflict Quarantine Manager.
====================================================
Quarantines logical entity keys (table:key) affected by unresolved multi-master conflicts in CentralStateStore.
Entity-scoped isolation prevents target apply for conflicting rows without pausing unrelated pipeline partitions.
"""

import uuid
import logging
import threading
import datetime
from typing import Dict, Any, List, Optional, Set

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.multi_master.domain import (
    CDCQuarantineRecord,
    CDCQuarantineState,
)
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator

logger = logging.getLogger("akaal.cdc.multi_master.quarantine")


class CDCConflictQuarantineManager:
    """
    Backend-authoritative conflict quarantine manager.
    Maintains entity-scoped quarantine locks in CentralStateStore.
    """

    def __init__(
        self,
        topology_id: str,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
    ) -> None:
        self.topology_id = topology_id
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self._lock = threading.RLock()

        self.quarantines: Dict[str, CDCQuarantineRecord] = {}
        self._quarantined_keys: Set[str] = set()  # Set of "table:key" strings
        self._load_persisted_quarantines()

    def _get_entity_lock_key(self, table: str, entity_key: str) -> str:
        return f"{table}:{entity_key}"

    def _load_persisted_quarantines(self) -> None:
        """Restores persisted quarantine records from CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            try:
                q_dict = self.state_store.get_state(f"cdc_quarantine_records_{self.topology_id}", category="quarantine_manager")
                if q_dict and isinstance(q_dict, dict):
                    for qid, qdata in q_dict.items():
                        rec = CDCQuarantineRecord.from_dict(qdata)
                        self.quarantines[qid] = rec
                        if rec.state not in (CDCQuarantineState.RELEASED, CDCQuarantineState.RESOLVED):
                            self._quarantined_keys.add(self._get_entity_lock_key(rec.entity_table, rec.entity_key))
                    logger.info(
                        f"[QuarantineManager] Restored {len(self.quarantines)} quarantine records "
                        f"({len(self._quarantined_keys)} active entity locks) for topology '{self.topology_id}'."
                    )
            except Exception as exc:
                fail = CDCFailure(
                    failure_type=CDCFailureType.QUARANTINE_FAILURE,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[QUARANTINE STATE CORRUPTION] Failed to restore quarantine records: {exc}",
                    migration_id="mig-unknown",
                    job_id="job-unknown",
                    run_id="run-unknown",
                    cdc_session_id="sess-unknown",
                )
                raise CDCExecutionError(fail)

    def _persist_quarantines(self) -> None:
        """Persists quarantine records into CentralStateStore."""
        if not self.state_store:
            return
        with self._lock:
            data = {
                qid: q.to_dict()
                for qid, q in self.quarantines.items()
            }
            self.state_store.set_state(f"cdc_quarantine_records_{self.topology_id}", data, category="quarantine_manager")


    def quarantine_entity(
        self,
        identity: CDCEventIdentity,
        conflict_id: str,
        entity_table: str,
        entity_key: str,
        reason: str,
        fencing_epoch: int,
    ) -> CDCQuarantineRecord:
        """
        Quarantines logical entity key (entity_table:entity_key).
        Prevents events modifying this key from reaching target apply.
        """
        with self._lock:
            # Fencing validation
            if not self.recovery_coordinator.validate_fencing_token(identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE WORKER] Stale epoch {fencing_epoch} rejected for quarantine acquisition '{entity_table}:{entity_key}'.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            lock_key = self._get_entity_lock_key(entity_table, entity_key)
            qid = f"quar-{uuid.uuid4().hex[:8]}"

            record = CDCQuarantineRecord(
                quarantine_id=qid,
                conflict_id=conflict_id,
                topology_id=self.topology_id,
                migration_id=identity.migration_id,
                run_id=identity.run_id,
                entity_table=entity_table,
                entity_key=entity_key,
                reason=reason,
                fencing_epoch=fencing_epoch,
                state=CDCQuarantineState.ACTIVE,
            )

            self.quarantines[qid] = record
            self._quarantined_keys.add(lock_key)
            self._persist_quarantines()

            from akaal.privacy.sanitizer import LogAndDiagnosticSanitizer
            sanitized_key = LogAndDiagnosticSanitizer.sanitize_text(lock_key)
            sanitized_reason = LogAndDiagnosticSanitizer.sanitize_text(reason)
            logger.warning(f"[QuarantineManager] Quarantined entity '{sanitized_key}' for conflict '{conflict_id}' (Quarantine ID: '{qid}'). Reason: {sanitized_reason}")
            return record

    def is_entity_quarantined(self, entity_table: str, entity_key: str) -> bool:
        """Returns True if logical entity key is currently quarantined."""
        with self._lock:
            lock_key = self._get_entity_lock_key(entity_table, entity_key)
            return lock_key in self._quarantined_keys

    def release_quarantine(
        self,
        identity: CDCEventIdentity,
        quarantine_id: str,
        resolution_id: str,
        fencing_epoch: int,
    ) -> CDCQuarantineRecord:
        """
        Releases quarantine lock for quarantine_id after resolution approval.
        Validates fencing epoch via RecoveryCoordinator.
        """
        with self._lock:
            # Fencing validation
            if not self.recovery_coordinator.validate_fencing_token(identity.migration_id, fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[STALE WORKER] Stale epoch {fencing_epoch} rejected for quarantine release '{quarantine_id}'.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            record = self.quarantines.get(quarantine_id)
            if not record:
                fail = CDCFailure(
                    failure_type=CDCFailureType.QUARANTINE_FAILURE,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[QUARANTINE NOT FOUND] Quarantine record '{quarantine_id}' does not exist.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            # Identity binding check
            if record.topology_id != self.topology_id or record.run_id != identity.run_id:
                fail = CDCFailure(
                    failure_type=CDCFailureType.TOPOLOGY_IDENTITY_MISMATCH,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[IDENTITY MISMATCH] Quarantine record run '{record.run_id}' does not match active run '{identity.run_id}'.",
                    migration_id=identity.migration_id,
                    job_id=identity.job_id,
                    run_id=identity.run_id,
                    cdc_session_id=identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            record.state = CDCQuarantineState.RELEASED
            record.resolution_id = resolution_id
            record.released_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            lock_key = self._get_entity_lock_key(record.entity_table, record.entity_key)
            self._quarantined_keys.discard(lock_key)
            self._persist_quarantines()

            logger.info(f"[QuarantineManager] Released quarantine '{quarantine_id}' for entity '{lock_key}'.")
            return record

    def get_active_quarantines(self) -> List[CDCQuarantineRecord]:
        """Returns list of active quarantine records."""
        with self._lock:
            return [q for q in self.quarantines.values() if q.state not in (CDCQuarantineState.RELEASED, CDCQuarantineState.RESOLVED)]
