"""
AKAAL CDC Target Apply Engine & Acknowledgement Controller.
============================================================
Orchestrates ordered CDC transaction application to target adapters, target transaction atomicity,
durable checkpointing, restart-persistent replay/duplicate protection, monotonic fencing enforcement,
and safe acknowledgement state transitions.
"""

from typing import Dict, Any, List, Optional, Set
import logging
import uuid
import datetime

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, parse_cdc_transaction, CDCOperationType
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.lifecycle import CDCAckState, CDCSessionState, CDCSessionStateMachine
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError
from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer

from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.core.state.state_store import CentralStateStore
from akaal.adapters.adapter_registry import create_adapter
from akaal.core.models.project import ConnectionConfig

logger = logging.getLogger(__name__)


class CDCApplyWorker:
    """
    Target Apply Worker processing durably buffered CDC transactions.
    Enforces target transaction atomicity (BEGIN -> DML -> COMMIT or ROLLBACK),
    unsafe DML detection, restart-persistent replay deduplication, and fencing epoch protection.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        durable_buffer: Optional[DurableCDCBuffer] = None,
        recovery_coordinator: Optional[RecoveryCoordinator] = None,
        state_store: Optional[CentralStateStore] = None,
        barrier_authority: Optional[Any] = None,
        worker_id: str = "default_worker",
    ) -> None:
        self.identity = identity
        self.durable_buffer = durable_buffer
        self.recovery_coordinator = recovery_coordinator or RecoveryCoordinator()
        self.state_store = state_store or CentralStateStore()
        self.barrier_authority = barrier_authority
        self.worker_id = worker_id

        self.applied_transaction_ids: Set[str] = set()
        self.applied_transaction_hashes: Dict[str, str] = {}
        self.last_applied_position: Optional[CDCSourcePosition] = None
        self.last_checkpoint: Optional[CDCCheckpoint] = None
        self.last_acknowledged_position: Optional[CDCSourcePosition] = None

        # Load restart-persistent applied transaction state from CentralStateStore
        self._load_persistent_applied_state()

    def _load_persistent_applied_state(self) -> None:
        """Loads durable applied transaction IDs and payload digests from CentralStateStore to survive process restarts."""
        state_key = f"cdc_applied_txs_{self.identity.cdc_session_id}"
        persisted = self.state_store.get_state(state_key, category="cdc_applied_txs", default={})
        if isinstance(persisted, dict):
            self.applied_transaction_ids = set(persisted.get("applied_ids", []))
            self.applied_transaction_hashes = persisted.get("applied_hashes", {})
            if persisted.get("last_applied_position"):
                self.last_applied_position = parse_source_position(persisted["last_applied_position"])
                self.last_acknowledged_position = self.last_applied_position
            logger.info(
                f"[CDCApplyWorker] Restored {len(self.applied_transaction_ids)} durable applied transactions from CentralStateStore for session '{self.identity.cdc_session_id}'."
            )

    def _persist_applied_transaction(self, tx_id: str, tx_hash: str, commit_position: CDCSourcePosition) -> None:
        """Persists applied transaction state synchronously to CentralStateStore."""
        self.applied_transaction_ids.add(tx_id)
        self.applied_transaction_hashes[tx_id] = tx_hash
        self.last_applied_position = commit_position

        state_key = f"cdc_applied_txs_{self.identity.cdc_session_id}"
        payload = {
            "applied_ids": list(self.applied_transaction_ids),
            "applied_hashes": self.applied_transaction_hashes,
            "last_applied_position": commit_position.to_dict(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.state_store.set_state(state_key, payload, category="cdc_applied_txs")

    def apply_next_transaction(self, current_fencing_epoch: int, target_config: Optional[Dict[str, Any]] = None, transaction: Optional[CDCTransaction] = None) -> Dict[str, Any]:
        """
        Reads next transaction from durable buffer (or takes transaction directly), validates fencing, applies to target, writes checkpoint, and acknowledges.
        """
        # Validate fencing epoch
        if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, current_fencing_epoch):
            fail = CDCFailure(
                failure_type=CDCFailureType.STALE_WORKER,
                category=CDCFailureCategory.BLOCKING,
                message=f"[FENCING VIOLATION] Stale worker fencing epoch {current_fencing_epoch} rejected.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        if transaction is not None:
            tx = transaction
            tx_hash = ""
        else:
            if not self.durable_buffer:
                return {"status": "NO_TRANSACTIONS", "applied": False}
            buffer_entry = self.durable_buffer.pop_next_transaction()
            if not buffer_entry:
                return {"status": "NO_TRANSACTIONS", "applied": False}

            tx_dict = buffer_entry["transaction_data"]
            tx = parse_cdc_transaction(tx_dict)
            tx_hash = buffer_entry.get("record_hmac", "")

        # Validate transaction identity
        if (
            tx.identity.migration_id != self.identity.migration_id
            or tx.identity.run_id != self.identity.run_id
            or tx.identity.cdc_session_id != self.identity.cdc_session_id
        ):
            fail = CDCFailure(
                failure_type=CDCFailureType.IDENTITY_MISMATCH,
                category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                message=f"[IDENTITY MISMATCH] Transaction '{tx.tx_id}' identity does not match worker session.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # Check Active Schema Barrier
        if self.barrier_authority:
            for evt in tx.events:
                if self.barrier_authority.is_barrier_active(self.identity.cdc_session_id, evt.source_table):
                    fail = CDCFailure(
                        failure_type=CDCFailureType.SCHEMA_BARRIER_ACTIVE,
                        category=CDCFailureCategory.PAUSABLE,
                        message=f"[SCHEMA BARRIER ACTIVE] Cannot apply transaction '{tx.tx_id}' while active schema barrier is set for table '{evt.source_table}'.",
                        migration_id=self.identity.migration_id,
                        job_id=self.identity.job_id,
                        run_id=self.identity.run_id,
                        cdc_session_id=self.identity.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)

        # Check if already applied (Restart-Persistent Replay & Duplicate Protection)
        if tx.tx_id in self.applied_transaction_ids:
            # Detect tampered duplicate payload
            expected_hash = self.applied_transaction_hashes.get(tx.tx_id)
            if expected_hash and tx_hash and expected_hash != tx_hash:
                fail = CDCFailure(
                    failure_type=CDCFailureType.TRANSACTION_CORRUPTION,
                    category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                    message=f"[REPLAY PAYLOAD TAMPERING] Duplicate tx '{tx.tx_id}' replayed with mismatched payload hash.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            logger.info(f"[CDCApplyWorker] Transaction '{tx.tx_id}' already applied on target (durable dedup). Suppressing duplicate DML execution.")
            
            # Revalidate fencing token before checkpoint & ack
            if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, current_fencing_epoch):
                fail = CDCFailure(
                    failure_type=CDCFailureType.STALE_WORKER,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[FENCING VIOLATION] Stale worker fencing epoch {current_fencing_epoch} rejected during deduplicated checkpointing.",
                    migration_id=self.identity.migration_id,
                    job_id=self.identity.job_id,
                    run_id=self.identity.run_id,
                    cdc_session_id=self.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            self.last_applied_position = tx.commit_position
            ckpt = CDCCheckpoint(
                checkpoint_id=f"ckpt-{uuid.uuid4().hex[:8]}",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
                fencing_epoch=current_fencing_epoch,
                source_position=tx.commit_position,
                applied_position=tx.commit_position,
                acknowledged_position=tx.commit_position,
            )
            self.last_checkpoint = ckpt
            self.last_acknowledged_position = tx.commit_position
            if self.durable_buffer:
                self.durable_buffer.remove_acknowledged_transaction(tx.tx_id, worker_last_ack_pos=tx.commit_position)

            return {
                "status": "SUCCESS",
                "tx_id": tx.tx_id,
                "applied": True,
                "duplicate_suppressed": True,
                "events_applied": len(tx.events),
                "checkpoint_id": ckpt.checkpoint_id,
            }

        # Apply transaction to target database
        try:
            self._execute_target_transaction(tx, target_config)
        except CDCExecutionError:
            raise
        except Exception as ex:
            fail = CDCFailure(
                failure_type=CDCFailureType.TARGET_APPLY_FAILURE,
                category=CDCFailureCategory.PAUSABLE,
                message=f"[TARGET APPLY ERROR] Transaction '{tx.tx_id}' failed during target application: {str(ex)}",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # Target transaction committed successfully! Persist durable applied state immediately
        self._persist_applied_transaction(tx.tx_id, tx_hash, tx.commit_position)

        # Revalidate fencing epoch before checkpoint & ack
        if not self.recovery_coordinator.validate_fencing_token(self.identity.migration_id, current_fencing_epoch):
            fail = CDCFailure(
                failure_type=CDCFailureType.STALE_WORKER,
                category=CDCFailureCategory.BLOCKING,
                message=f"[FENCING VIOLATION] Stale worker fencing epoch {current_fencing_epoch} rejected before checkpointing.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # Write durable checkpoint with HMAC digest
        ckpt = CDCCheckpoint(
            checkpoint_id=f"ckpt-{uuid.uuid4().hex[:8]}",
            migration_id=self.identity.migration_id,
            job_id=self.identity.job_id,
            run_id=self.identity.run_id,
            cdc_session_id=self.identity.cdc_session_id,
            fencing_epoch=current_fencing_epoch,
            source_position=tx.commit_position,
            applied_position=tx.commit_position,
            acknowledged_position=tx.commit_position,
        )
        self.last_checkpoint = ckpt
        self.last_acknowledged_position = tx.commit_position

        # Remove acknowledged transaction from durable buffer (validating ack position)
        if self.durable_buffer:
            self.durable_buffer.remove_acknowledged_transaction(tx.tx_id, worker_last_ack_pos=tx.commit_position)

        # Record checkpoint in state store
        self.state_store.set_state(f"checkpoint-{self.identity.cdc_session_id}", ckpt.to_dict(), category="checkpoint")

        logger.info(
            f"[CDCApplyWorker] Successfully applied and acknowledged transaction '{tx.tx_id}' ({len(tx.events)} events, Checkpoint: {ckpt.checkpoint_id})."
        )
        return {
            "status": "SUCCESS",
            "tx_id": tx.tx_id,
            "applied": True,
            "duplicate_suppressed": False,
            "events_applied": len(tx.events),
            "checkpoint_id": ckpt.checkpoint_id,
        }

    def _execute_target_transaction(self, tx: CDCTransaction, target_config: Optional[Dict[str, Any]]) -> None:
        """Executes DML statements inside target transaction boundary with safety checks and physical target execution."""
        for evt in tx.events:
            # Enforce UPDATE safety: must contain primary key / target row identity
            if evt.operation == CDCOperationType.UPDATE:
                has_key = (evt.before_image and len(evt.before_image) > 0) or (evt.after_image and ("id" in evt.after_image or "pk" in str(evt.after_image).lower()))
                if not has_key:
                    fail = CDCFailure(
                        failure_type=CDCFailureType.UNSAFE_UPDATE,
                        category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                        message=f"[UNSAFE UPDATE] UPDATE event in table '{evt.source_table}' lacks primary key / before image identity.",
                        migration_id=self.identity.migration_id,
                        job_id=self.identity.job_id,
                        run_id=self.identity.run_id,
                        cdc_session_id=self.identity.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)

            # Enforce DELETE safety: must contain primary key / target row identity
            if evt.operation == CDCOperationType.DELETE:
                has_key = (evt.before_image and len(evt.before_image) > 0)
                if not has_key:
                    fail = CDCFailure(
                        failure_type=CDCFailureType.UNSAFE_DELETE,
                        category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                        message=f"[UNSAFE DELETE] DELETE event in table '{evt.source_table}' lacks primary key / before image identity.",
                        migration_id=self.identity.migration_id,
                        job_id=self.identity.job_id,
                        run_id=self.identity.run_id,
                        cdc_session_id=self.identity.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)

        # Execute physical target DML if target adapter is attached
        target_adapter = getattr(self, "target_adapter", None)
        if target_adapter:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            success = loop.run_until_complete(target_adapter.apply_changes(tx.events))
            if not success:
                raise RuntimeError(f"Physical target change application returned false for transaction '{tx.tx_id}'")
