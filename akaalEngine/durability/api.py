"""
Canonical Public Façade for Authority #5 — Durability (`DurabilityAuthority`).
"""

import os
import logging
from typing import Dict, Any, Iterator, List, Optional

logger = logging.getLogger("akaalEngine.durability.api")

from akaalEngine.durability.models import (
    DurabilityConfig,
    StateRecord,
    StateVersion,
    MigrationCheckpoint,
    RowPosition,
    OperationRecord,
    QueueMessageRef,
    FencingToken,
    ExecutionManifest,
)
from akaalEngine.durability.recovery.idempotency import IdempotencyState, IdempotencyRegistry
from akaalEngine.durability.recovery.inspector import DurableRecoverySnapshot, RecoveryStateInspector
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.durability.store.cas import StateCasCoordinator
from akaalEngine.durability.checkpoint.registry import MigrationCheckpointRegistry
from akaalEngine.durability.journal.store import OperationJournalStore
from akaalEngine.durability.journal.compaction import JournalCompactionEngine
from akaalEngine.durability.spill.spooler import BoundedDiskSpooler, SpilledSegmentRef
from akaalEngine.durability.spill.queue_store import DurableQueueStore
from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.integrity.quota import StorageQuotaMonitor
from akaalEngine.durability.models.errors import FencingViolationError, DurabilityError, DurabilityConfigError


class DurabilityAuthority:
    """Single Canonical Entrypoint and Façade for Authority #5 — Durability."""

    def __init__(self, config: DurabilityConfig, backend: Optional[SQLiteWalBackend] = None) -> None:
        self.config = config
        os.makedirs(config.storage_dir, exist_ok=True)

        self.quota_monitor = StorageQuotaMonitor(
            storage_dir=config.storage_dir,
            quota_bytes=config.spill_quota_bytes,
            reserve_bytes=config.disk_reserve_bytes,
        )

        self.backend = backend or SQLiteWalBackend(config, quota_monitor=self.quota_monitor)
        self.backend.initialize()

        # Validate required key material
        if not config.fencing_signing_key or not isinstance(config.fencing_signing_key, bytes):
            raise DurabilityConfigError("Fencing signing key is required and must be non-empty bytes.")
        if not config.journal_anchor_key or not isinstance(config.journal_anchor_key, bytes):
            raise DurabilityConfigError("Journal anchor HMAC key is required and must be non-empty bytes.")
        if config.fencing_signing_key == config.journal_anchor_key:
            raise DurabilityConfigError("Fencing signing key and journal anchor key must be domain-separated (distinct keys).")

        self.cas_coordinator = StateCasCoordinator(self.backend)
        self.fencing_manager = FencingTokenManager(self.backend, signing_key=config.fencing_signing_key)

        self.checkpoint_registry = MigrationCheckpointRegistry(self.backend)
        # Wire fencing manager — registry cannot operate without it
        self.checkpoint_registry._fencing_manager = self.fencing_manager

        self.journal_store = OperationJournalStore(self.backend)
        self.compaction_engine = JournalCompactionEngine(self.backend, anchor_key=config.journal_anchor_key)
        # Wire compaction engine into journal store so verify_chain_integrity uses HMAC anchors
        self.journal_store._compaction_engine = self.compaction_engine


        self.idempotency_registry = IdempotencyRegistry(self.backend)
        self.recovery_inspector = RecoveryStateInspector(self.backend)

        spool_dir = os.path.join(config.storage_dir, "spool")
        self.spooler = BoundedDiskSpooler(spool_dir=spool_dir, quota_monitor=self.quota_monitor)
        self.queue_store = DurableQueueStore(self.backend)

    def close(self) -> None:
        """Closes all tracked SQLite connections."""
        self.backend.close()

    # --- State Store & CAS (DUR-001, DUR-005) ---
    def put_state(self, record: StateRecord) -> StateVersion:
        return self.backend.put_state(record)

    def get_state(self, key: str, namespace: str) -> Optional[StateRecord]:
        return self.backend.get_state(key, namespace)

    def compare_and_swap(self, key: str, namespace: str, expected_version: int, new_payload: Dict[str, Any]) -> StateVersion:
        return self.cas_coordinator.cas_update(key, namespace, expected_version, new_payload)

    # --- Fencing Tokens (DUR-006) — must be called first ---
    def issue_fencing_token(self, resource_id: str, worker_id: str) -> FencingToken:
        return self.fencing_manager.issue_token(resource_id, worker_id)

    def validate_fencing_token(self, token: FencingToken) -> bool:
        return self.fencing_manager.validate_token(token)

    def validate_fencing_envelope(self, envelope: Dict[str, Any]) -> bool:
        """Validates boundary-neutral fencing token envelope."""
        if not isinstance(envelope, dict):
            return False
        res_id = envelope.get("resource_id") or envelope.get("canonical_resource_id")
        worker_id = envelope.get("worker_id") or envelope.get("owner_id", "gateway")
        epoch = envelope.get("fencing_epoch") or envelope.get("epoch", 0)
        issued_at = envelope.get("issued_at") or envelope.get("timestamp", "")
        sig = envelope.get("signature") or envelope.get("engine_signature", "")
        if not res_id or not worker_id or not sig:
            return False
        token = FencingToken(
            resource_id=res_id,
            worker_id=worker_id,
            fencing_epoch=int(epoch),
            issued_at=issued_at,
            signature=sig,
        )
        return self.validate_fencing_token(token)

    def get_current_epoch(self, resource_id: str) -> int:
        """Returns live fencing epoch for a resource without mutating state."""
        conn = self.backend._get_connection()
        cursor = conn.execute("SELECT current_epoch FROM fencing_tokens WHERE resource_id = ?;", (resource_id,))
        row = cursor.fetchone()
        return row["current_epoch"] if row else 0

    # --- Hierarchical Checkpoints & Positions (DUR-002, DUR-003) ---
    def save_checkpoint(self, checkpoint: MigrationCheckpoint, token: FencingToken) -> None:
        """Saves checkpoint. Requires an authenticated FencingToken — no bypass."""
        self.checkpoint_registry.save_checkpoint(checkpoint, token)

    def get_checkpoint(self, checkpoint_id: str, migration_id: Optional[str] = None, run_id: Optional[str] = None) -> Optional[MigrationCheckpoint]:
        return self.checkpoint_registry.get_checkpoint(checkpoint_id, migration_id=migration_id, run_id=run_id)

    def get_latest_checkpoint(self, migration_id: str) -> Optional[MigrationCheckpoint]:
        return self.checkpoint_registry.get_latest_checkpoint(migration_id)

    def recover_checkpoint(self, checkpoint_id: str, migration_id: Optional[str] = None, run_id: Optional[str] = None) -> MigrationCheckpoint:
        """Recovers exact durable checkpoint state. Fails closed if missing."""
        chk = self.get_checkpoint(checkpoint_id, migration_id=migration_id, run_id=run_id)
        if chk is None:
            raise DurabilityError(f"Checkpoint recovery failed: Checkpoint '{checkpoint_id}' not found for migration '{migration_id}'.")
        return chk

    def save_row_position(self, migration_id: str, table_name: str, position: RowPosition, token: FencingToken) -> None:
        """Advances table row position. Requires an authenticated FencingToken — no bypass."""
        self.checkpoint_registry.save_row_position(migration_id, table_name, position, token)

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        import re
        pattern = r'(password|secret|token|key|pwd|cred|credential)\s*[=:]\s*([^\s,;]+)'
        return re.sub(pattern, r'\1=[REDACTED]', text, flags=re.IGNORECASE)

    # --- Transaction Batch Rollback ---
    def verify_batch_exists(self, batch_id: str) -> bool:
        """Verifies if batch_id exists in checkpoints, idempotency records, or journal store."""
        conn = self.backend._get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM checkpoints WHERE job_id = ? "
            "UNION SELECT 1 FROM idempotency_records WHERE idempotency_key = ? "
            "UNION SELECT 1 FROM journal_records WHERE operation_id = ?;",
            (batch_id, batch_id, batch_id),
        )
        return cursor.fetchone() is not None

    def get_batch_migration_id(self, batch_id: str) -> Optional[str]:
        """Fetches the bound migration_id for a given batch_id from durability store with deterministic ownership check."""
        conn = self.backend._get_connection()
        cursor = conn.execute(
            "SELECT migration_id FROM checkpoints WHERE job_id = ? AND migration_id IS NOT NULL AND migration_id != '' "
            "UNION SELECT migration_id FROM idempotency_records WHERE idempotency_key = ? AND migration_id IS NOT NULL AND migration_id != '' "
            "UNION SELECT migration_id FROM journal_records WHERE operation_id = ? AND migration_id IS NOT NULL AND migration_id != '';",
            (batch_id, batch_id, batch_id),
        )
        rows = cursor.fetchall()
        distinct = {r[0] for r in rows if r and r[0]}
        if len(distinct) > 1:
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Ambiguous batch ownership: batch_id '{batch_id}' is associated with multiple distinct migration IDs: {sorted(list(distinct))}")
        return next(iter(distinct)) if distinct else None

    def get_batch_endpoint_identity(self, batch_id: str) -> Optional[str]:
        """Fetches the bound target endpoint_identity for a given batch_id from durability store."""
        conn = self.backend._get_connection()
        cursor = conn.execute(
            "SELECT json_extract(checkpoint_json, '$.endpoint_identity') FROM checkpoints WHERE job_id = ? AND json_extract(checkpoint_json, '$.endpoint_identity') IS NOT NULL;",
            (batch_id,),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def stage_pending_rollback(self, batch_id: str) -> None:
        """Stages PENDING_ROLLBACK state in Durability store before physical target rollback is executed."""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        mig_id = self.get_batch_migration_id(batch_id) or ""
        conn = self.backend._get_connection()
        with conn:
            conn.execute(
                "UPDATE checkpoints SET checkpoint_json = json_set(checkpoint_json, '$.status', 'PENDING_ROLLBACK'), updated_at = ? WHERE job_id = ?;",
                (now, batch_id),
            )
            self.journal_store.append_record(
                operation_id=f"pending-rollback-{batch_id}",
                operation_type="PENDING_ROLLBACK",
                payload={"batch_id": batch_id, "action": "STAGE_PENDING_ROLLBACK"},
                migration_id=mig_id,
                conn=conn,
            )

    def record_rollback_failure(self, batch_id: str, error_msg: str) -> None:
        """Records ROLLBACK_FAILED state in Durability store if physical target rollback fails."""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        mig_id = self.get_batch_migration_id(batch_id) or ""
        safe_error = self._sanitize_text(error_msg)
        conn = self.backend._get_connection()
        with conn:
            conn.execute(
                "UPDATE checkpoints SET checkpoint_json = json_set(checkpoint_json, '$.status', 'ROLLBACK_FAILED'), updated_at = ? WHERE job_id = ?;",
                (now, batch_id),
            )
            self.journal_store.append_record(
                operation_id=f"rollback-failed-{batch_id}",
                operation_type="ROLLBACK_FAILED",
                payload={"batch_id": batch_id, "error": safe_error},
                migration_id=mig_id,
                conn=conn,
            )

    def rollback_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Executes physical transaction batch rollback for a given batch_id.
        Verifies existence of batch_id in checkpoints/idempotency/journal records (fails closed if unknown),
        appends a compensation tombstone record to operation_journal, updates matching checkpoint
        status to ROLLED_BACK, and transitions idempotency state.
        """
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not self.verify_batch_exists(batch_id):
            from akaalEngine.durability.models.errors import DurabilityError
            raise DurabilityError(f"Rollback rejected: no checkpoint, idempotency record, or journal entry found for batch_id '{batch_id}'.")

        mig_id = self.get_batch_migration_id(batch_id) or ""
        conn = self.backend._get_connection()
        with conn:
            conn.execute(
                "UPDATE checkpoints SET checkpoint_json = json_set(checkpoint_json, '$.status', 'ROLLED_BACK'), updated_at = ? WHERE job_id = ?;",
                (now, batch_id),
            )
            conn.execute(
                "UPDATE idempotency_records SET state = 'ABANDONED', updated_at = ? WHERE idempotency_key = ?;",
                (now, batch_id),
            )
            tombstone = self.journal_store.append_record(
                operation_id=f"rollback-{batch_id}",
                operation_type="ROLLBACK_BATCH",
                payload={"batch_id": batch_id, "action": "ROLLBACK_TOMBSTONE"},
                migration_id=mig_id,
                conn=conn,
            )

        return {
            "batch_id": batch_id,
            "status": "ROLLED_BACK",
            "tombstone_id": getattr(tombstone, "journal_id", f"journal-{batch_id}"),
            "timestamp": now,
        }

        logger.info(f"[DurabilityAuthority] Executed physical rollback for batch '{batch_id}'. Tombstone operation ID: '{tombstone.operation_id}'.")
        return {
            "batch_id": batch_id,
            "status": "ROLLED_BACK",
            "tombstone_operation_id": tombstone.operation_id,
            "rolled_back": True,
        }

    # --- Operation Journal & Retention (DUR-004, DUR-013) ---
    def append_journal_record(self, operation_id: str, operation_type: str, payload: Dict[str, Any], migration_id: str = "") -> OperationRecord:
        return self.journal_store.append_record(operation_id, operation_type, payload, migration_id=migration_id)

    def verify_journal_integrity(self) -> bool:
        return self.journal_store.verify_chain_integrity()

    def compact_journal(self, safe_sequence_boundary: int) -> int:
        return self.compaction_engine.compact_journal(safe_sequence_boundary)

    def purge_expired_journal_records(self, max_age_days: int) -> int:
        return self.compaction_engine.purge_expired_records(max_age_days)

    # --- Idempotency & Deduplication (DUR-008) ---
    def get_idempotency_state(self, idempotency_key: str) -> Optional[IdempotencyState]:
        return self.idempotency_registry.get_state(idempotency_key)

    def transition_idempotency_state(
        self,
        idempotency_key: str,
        expected_state: Optional[IdempotencyState],
        new_state: IdempotencyState,
        fencing_epoch: int,
        input_fingerprint: str,
        result_hash: Optional[str] = None,
        migration_id: str = "",
    ) -> bool:
        return self.idempotency_registry.transition_state(
            idempotency_key=idempotency_key,
            expected_state=expected_state,
            new_state=new_state,
            fencing_epoch=fencing_epoch,
            input_fingerprint=input_fingerprint,
            result_hash=result_hash,
            migration_id=migration_id,
        )

    # --- Bounded Disk Spooler & Persistent Queue (DUR-009, DUR-010) ---
    def spill_data(self, stream_id: str, payload: bytes) -> SpilledSegmentRef:
        return self.spooler.spill_data(stream_id, payload)

    def stream_spilled_data(self, ref: SpilledSegmentRef, chunk_size: int = 65536) -> Iterator[bytes]:
        return self.spooler.stream_spilled_data(ref, chunk_size=chunk_size)

    def read_spilled_data(self, ref: SpilledSegmentRef) -> bytes:
        return self.spooler.read_spilled_data(ref)

    def delete_spilled_data(self, ref: SpilledSegmentRef) -> bool:
        return self.spooler.delete_spilled_segment(ref)

    def store_queue_message(self, queue_name: str, payload: bytes) -> str:
        return self.queue_store.store_message(queue_name, payload)

    def claim_queue_message(self, queue_name: str, worker_id: str, lease_duration_sec: int) -> Optional[QueueMessageRef]:
        return self.queue_store.claim_message(queue_name, worker_id, lease_duration_sec)

    def ack_queue_message(self, message_id: str, claimed_by: str, claim_id: str) -> bool:
        """ACK requires both claimed_by and claim_id — ownerless ACK is not permitted."""
        return self.queue_store.ack_message(message_id, claimed_by=claimed_by, claim_id=claim_id)

    # --- Execution Manifests (DUR-014) ---
    def save_execution_manifest(self, manifest: ExecutionManifest) -> None:
        self.backend.save_execution_manifest(manifest)

    def get_execution_manifest(self, manifest_id: str) -> Optional[ExecutionManifest]:
        return self.backend.get_execution_manifest(manifest_id)

    # --- State Inspection (DUR-007) ---
    def inspect_recovery_state(self, migration_id: str) -> DurableRecoverySnapshot:
        return self.recovery_inspector.inspect_recovery_state(migration_id)

    # --- Composed Shared Transactions (DUR-001) ---
    def save_checkpoint_with_journal(
        self,
        checkpoint: MigrationCheckpoint,
        token: FencingToken,
        operation_id: str,
        operation_type: str,
        journal_payload: Dict[str, Any],
        migration_id: str = "",
    ) -> OperationRecord:
        """Atomically saves checkpoint AND appends journal record in a single SQLite transaction."""
        conn = self.backend._get_connection()
        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")
                self.checkpoint_registry.save_checkpoint(checkpoint, token, conn=conn)
                op_rec = self.journal_store.append_record(operation_id, operation_type, journal_payload, migration_id=migration_id, conn=conn)
                conn.execute("COMMIT;")
                return op_rec
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    def transition_idempotency_with_checkpoint(
        self,
        idempotency_key: str,
        expected_state: Optional[IdempotencyState],
        new_state: IdempotencyState,
        fencing_epoch: int,
        input_fingerprint: str,
        checkpoint: MigrationCheckpoint,
        token: FencingToken,
        result_hash: Optional[str] = None,
        migration_id: str = "",
    ) -> bool:
        """Atomically transitions idempotency state AND updates checkpoint in a single transaction."""
        conn = self.backend._get_connection()
        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")
                self.idempotency_registry.transition_state(
                    idempotency_key=idempotency_key,
                    expected_state=expected_state,
                    new_state=new_state,
                    fencing_epoch=fencing_epoch,
                    input_fingerprint=input_fingerprint,
                    result_hash=result_hash,
                    migration_id=migration_id,
                    conn=conn,
                )
                self.checkpoint_registry.save_checkpoint(checkpoint, token, conn=conn)
                conn.execute("COMMIT;")
                return True
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    def ack_queue_with_position(
        self,
        message_id: str,
        claimed_by: str,
        claim_id: str,
        migration_id: str,
        table_name: str,
        position: RowPosition,
        token: FencingToken,
    ) -> bool:
        """
        Atomically ACKs queue message AND updates row position in a single transaction.
        If ACK fails (stale/wrong claim), position is NOT advanced — true all-or-nothing.
        """
        conn = self.backend._get_connection()
        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")
                ack_res = self.queue_store.ack_message(message_id, claimed_by=claimed_by, claim_id=claim_id, conn=conn)
                self.checkpoint_registry.save_row_position(migration_id, table_name, position, token, conn=conn)
                conn.execute("COMMIT;")
                return ack_res
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    # --- Capacity & Quota (DUR-012) ---
    def get_capacity_facts(self) -> Dict[str, Any]:
        return self.quota_monitor.get_capacity_facts()
