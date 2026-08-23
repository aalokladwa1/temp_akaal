"""
Durable Recovery State Inspector for Authority #5 — Durability (DUR-007).
Blocker 6 fix: queries use explicit migration_id column, not LIKE substring matching.
"""

from dataclasses import dataclass
from typing import List, Optional
from akaalEngine.durability.models.checkpoint import MigrationCheckpoint
from akaalEngine.durability.checkpoint.registry import MigrationCheckpointRegistry
from akaalEngine.durability.journal.store import OperationJournalStore
from akaalEngine.durability.recovery.idempotency import IdempotencyRegistry, IdempotencyState
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


@dataclass(frozen=True)
class DurableRecoverySnapshot:
    """Surviving durable state facts for restart reconstruction."""
    migration_id: str
    latest_checkpoint: Optional[MigrationCheckpoint]
    journal_records_count: int
    journal_is_valid: bool
    incomplete_idempotency_keys: List[str]
    committed_idempotency_keys: List[str]
    current_fencing_epoch: int


class RecoveryStateInspector:
    """Inspects surviving durable state for a specific migration after process or machine restart."""

    def __init__(self, backend: SQLiteWalBackend) -> None:
        self.backend = backend
        self.checkpoint_registry = MigrationCheckpointRegistry(backend)
        self.journal_store = OperationJournalStore(backend)
        self.idempotency_registry = IdempotencyRegistry(backend)

    def inspect_recovery_state(self, migration_id: str) -> DurableRecoverySnapshot:
        """
        Collects surviving durable facts scoped to a specific migration_id using
        explicit indexed column queries — NOT LIKE substring matching.
        """
        latest_chk = self.checkpoint_registry.get_latest_checkpoint(migration_id)
        journal_valid = False
        try:
            journal_valid = self.journal_store.verify_chain_integrity()
        except Exception:
            journal_valid = False

        conn = self.backend._get_connection()

        # Blocker 6 fix: count by explicit migration_id column (indexed), not LIKE JSON body
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM journal_records WHERE migration_id = ?;",
            (migration_id,)
        )
        row = cursor.fetchone()
        journal_count = row["cnt"] if row else 0

        # Blocker 6 fix: query idempotency by explicit migration_id column (indexed)
        cursor = conn.execute(
            "SELECT idempotency_key, state FROM idempotency_records WHERE migration_id = ?;",
            (migration_id,)
        )
        idemp_rows = cursor.fetchall()
        incomplete_keys = []
        committed_keys = []
        for r in idemp_rows:
            st = r["state"]
            if st in (IdempotencyState.RESERVED.value, IdempotencyState.IN_PROGRESS.value):
                incomplete_keys.append(r["idempotency_key"])
            elif st == IdempotencyState.COMMITTED.value:
                committed_keys.append(r["idempotency_key"])

        fencing_epoch = latest_chk.fencing_epoch if latest_chk else 0

        return DurableRecoverySnapshot(
            migration_id=migration_id,
            latest_checkpoint=latest_chk,
            journal_records_count=journal_count,
            journal_is_valid=journal_valid,
            incomplete_idempotency_keys=incomplete_keys,
            committed_idempotency_keys=committed_keys,
            current_fencing_epoch=fencing_epoch,
        )
