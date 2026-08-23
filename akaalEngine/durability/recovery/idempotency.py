"""
Idempotency & Operation Deduplication Registry for Authority #5 — Durability (DUR-008).
"""

import datetime
import sqlite3
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from akaalEngine.durability.models.errors import CASConflictError, StaleGenerationError, DurabilityError
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class IdempotencyState(str, Enum):
    RESERVED = "RESERVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class IdempotencyRegistry:
    """Manages 5-state idempotency records preventing duplicate execution replay."""

    ALLOWED_TRANSITIONS: Dict[IdempotencyState, Tuple[IdempotencyState, ...]] = {
        IdempotencyState.RESERVED: (IdempotencyState.IN_PROGRESS, IdempotencyState.ABANDONED),
        IdempotencyState.IN_PROGRESS: (IdempotencyState.COMMITTED, IdempotencyState.FAILED, IdempotencyState.ABANDONED),
        IdempotencyState.FAILED: (IdempotencyState.IN_PROGRESS, IdempotencyState.ABANDONED),
        IdempotencyState.ABANDONED: (IdempotencyState.RESERVED, IdempotencyState.IN_PROGRESS),
        IdempotencyState.COMMITTED: (),  # Terminal state
    }

    def __init__(self, backend: SQLiteWalBackend) -> None:
        self.backend = backend

    def get_state(self, idempotency_key: str, conn: Optional[sqlite3.Connection] = None) -> Optional[IdempotencyState]:
        """Gets current idempotency state."""
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute("SELECT state FROM idempotency_records WHERE idempotency_key = ?;", (idempotency_key,))
        row = cursor.fetchone()
        return IdempotencyState(row["state"]) if row else None

    def transition_state(
        self,
        idempotency_key: str,
        expected_state: Optional[IdempotencyState],
        new_state: IdempotencyState,
        fencing_epoch: int,
        input_fingerprint: str,
        result_hash: Optional[str] = None,
        migration_id: str = "",
        conn: Optional[sqlite3.Connection] = None,
    ) -> bool:
        """Executes a validated CAS transition on an idempotency key."""
        if SecretSanitizationFilter.contains_prohibited_secrets(input_fingerprint) or SecretSanitizationFilter.contains_prohibited_secrets(result_hash):
            raise DurabilityError("Prohibited Tier 1 authentication material detected in idempotency transition.")

        self.backend.validate_quota(len(input_fingerprint.encode("utf-8")) + (len(result_hash.encode("utf-8")) if result_hash else 0))
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                cursor = use_conn.execute(
                    "SELECT state, fencing_epoch, input_fingerprint FROM idempotency_records WHERE idempotency_key = ?;",
                    (idempotency_key,)
                )
                row = cursor.fetchone()

                if row is None:
                    if expected_state is not None:
                        raise CASConflictError(f"Idempotency transition failed: key '{idempotency_key}' does not exist (expected {expected_state.value}).")
                    use_conn.execute("""
                        INSERT INTO idempotency_records (idempotency_key, migration_id, state, result_hash, fencing_epoch, input_fingerprint, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (idempotency_key, migration_id, new_state.value, result_hash, fencing_epoch, input_fingerprint, now))
                else:
                    curr_state = IdempotencyState(row["state"])
                    curr_epoch = row["fencing_epoch"]
                    curr_fingerprint = row["input_fingerprint"]

                    # Reject input fingerprint divergence
                    if curr_fingerprint != input_fingerprint:
                        raise CASConflictError(
                            f"Idempotency transition rejected: input fingerprint mismatch for key '{idempotency_key}'."
                        )

                    if fencing_epoch < curr_epoch:
                        raise StaleGenerationError(f"Idempotency update rejected: epoch {fencing_epoch} is lower than current epoch {curr_epoch}.")

                    if expected_state is not None and curr_state != expected_state:
                        raise CASConflictError(f"Idempotency transition conflict for key '{idempotency_key}': current state is {curr_state.value}, expected {expected_state.value}.")

                    allowed = self.ALLOWED_TRANSITIONS.get(curr_state, ())
                    if new_state not in allowed:
                        raise CASConflictError(f"Illegal idempotency transition for key '{idempotency_key}' from {curr_state.value} to {new_state.value}.")

                    use_conn.execute("""
                        UPDATE idempotency_records SET
                            state = ?,
                            result_hash = ?,
                            fencing_epoch = ?,
                            input_fingerprint = ?,
                            updated_at = ?
                        WHERE idempotency_key = ?;
                    """, (new_state.value, result_hash, fencing_epoch, input_fingerprint, now, idempotency_key))

                if own_tx:
                    use_conn.execute("COMMIT;")
                return True
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise CASConflictError(f"Idempotency transition failed: {e}")
