"""
Cryptographic Operation Journal Store for Authority #5 — Durability (DUR-004).
"""

import datetime
import hashlib
import json
import sqlite3
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from akaalEngine.durability.journal.compaction import JournalCompactionEngine

from akaalEngine.durability.models.journal import OperationRecord, JournalBatch
from akaalEngine.durability.models.errors import JournalCorruptError, JournalSequenceConflictError, DurabilityError
from akaalEngine.durability.integrity.sanitizer import StateIntegritySanitizer
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class OperationJournalStore:
    """Append-only cryptographic operation journal store with SHA-256 hash-chaining verification."""

    GENESIS_HASH: str = "0" * 64

    def __init__(self, backend: SQLiteWalBackend) -> None:
        self.backend = backend
        # Lazily set by DurabilityAuthority to avoid circular import
        self._compaction_engine: Optional["JournalCompactionEngine"] = None

    def get_last_parent_hash(self, conn: Optional[sqlite3.Connection] = None) -> str:
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute("SELECT checksum FROM journal_records ORDER BY sequence_number DESC LIMIT 1;")
        row = cursor.fetchone()
        return row["checksum"] if row else self.GENESIS_HASH

    def append_record(
        self,
        operation_id: str,
        operation_type: str,
        payload: Dict[str, Any],
        migration_id: str = "",
        conn: Optional[sqlite3.Connection] = None,
    ) -> OperationRecord:
        """Appends an operation record to the journal, verifying parent hash-chain continuity."""
        SecretSanitizationFilter.sanitize_state_dict(payload)
        payload_json = json.dumps(payload, sort_keys=True)
        self.backend.validate_quota(len(payload_json.encode("utf-8")))

        payload_hash = StateIntegritySanitizer.compute_dict_checksum(payload)
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                parent_hash = self.get_last_parent_hash(use_conn)
                cursor = use_conn.execute("SELECT MAX(sequence_number) as max_seq FROM journal_records;")
                row = cursor.fetchone()
                seq = (row["max_seq"] or 0) + 1 if row and row["max_seq"] is not None else 1

                record_data = f"{seq}|{operation_id}|{operation_type}|{payload_hash}|{parent_hash}|{created_at}"
                checksum = hashlib.sha256(record_data.encode("utf-8")).hexdigest()

                use_conn.execute("""
                    INSERT INTO journal_records (operation_id, migration_id, sequence_number, operation_type, payload_json, payload_hash, parent_hash, checksum, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (operation_id, migration_id, seq, operation_type, payload_json, payload_hash, parent_hash, checksum, created_at))

                if own_tx:
                    use_conn.execute("COMMIT;")

                return OperationRecord(
                    operation_id=operation_id,
                    sequence_number=seq,
                    operation_type=operation_type,
                    payload=payload,
                    payload_hash=payload_hash,
                    parent_hash=parent_hash,
                    checksum=checksum,
                    created_at=created_at,
                )
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise JournalCorruptError(f"Failed to append operation record to journal: {e}")

    def verify_chain_integrity(self, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Blocker 4 fix: uses compaction anchor (if present) to seed expected_parent_hash.
        This means only legitimate compaction that persisted an anchor passes verification.
        Arbitrary/malicious prefix deletion lacks an anchor and will fail unless the deleted
        records happen to start from genesis — which cannot be forged without the HMAC key.
        """
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute(
            "SELECT sequence_number, operation_id, operation_type, payload_json, payload_hash, parent_hash, checksum, created_at FROM journal_records ORDER BY sequence_number ASC;"
        )
        rows = cursor.fetchall()
        if not rows:
            return True

        # Determine the expected starting parent from the compaction anchor (if any)
        if self._compaction_engine is not None:
            expected_start_seq, expected_parent = self._compaction_engine.get_chain_start_parent_hash(use_conn)
        else:
            expected_start_seq = 1
            expected_parent = self.GENESIS_HASH

        first_seq = rows[0]["sequence_number"]
        if first_seq != expected_start_seq:
            raise JournalSequenceConflictError(
                f"Journal chain start mismatch: expected sequence {expected_start_seq}, found {first_seq}. "
                f"Missing compaction anchor for this boundary."
            )

        expected_seq = first_seq

        for row in rows:
            seq = row["sequence_number"]
            if seq != expected_seq:
                raise JournalSequenceConflictError(f"Journal sequence non-contiguous: expected {expected_seq}, found {seq}.")

            payload = json.loads(row["payload_json"])
            actual_payload_hash = StateIntegritySanitizer.compute_dict_checksum(payload)
            if actual_payload_hash != row["payload_hash"]:
                raise JournalCorruptError(f"Journal payload hash corrupted for operation '{row['operation_id']}'.")

            if row["parent_hash"] != expected_parent:
                raise JournalCorruptError(
                    f"Journal hash chain broken at sequence {seq}: expected parent '{expected_parent}', found '{row['parent_hash']}'."
                )

            record_data = f"{seq}|{row['operation_id']}|{row['operation_type']}|{row['payload_hash']}|{row['parent_hash']}|{row['created_at']}"
            computed_checksum = hashlib.sha256(record_data.encode("utf-8")).hexdigest()
            if computed_checksum != row["checksum"]:
                raise JournalCorruptError(f"Journal record checksum mismatch at sequence {seq}.")

            expected_parent = row["checksum"]
            expected_seq += 1

        return True

    def get_records_since(self, start_sequence: int = 1, migration_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[OperationRecord]:
        """Reads operation records starting from start_sequence, optionally scoped to a migration_id."""
        use_conn = conn or self.backend._get_connection()
        if migration_id is not None:
            cursor = use_conn.execute(
                "SELECT sequence_number, operation_id, operation_type, payload_json, payload_hash, parent_hash, checksum, created_at FROM journal_records WHERE sequence_number >= ? AND migration_id = ? ORDER BY sequence_number ASC;",
                (start_sequence, migration_id)
            )
        else:
            cursor = use_conn.execute(
                "SELECT sequence_number, operation_id, operation_type, payload_json, payload_hash, parent_hash, checksum, created_at FROM journal_records WHERE sequence_number >= ? ORDER BY sequence_number ASC;",
                (start_sequence,)
            )
        rows = cursor.fetchall()
        return [
            OperationRecord(
                operation_id=row["operation_id"],
                sequence_number=row["sequence_number"],
                operation_type=row["operation_type"],
                payload=json.loads(row["payload_json"]),
                payload_hash=row["payload_hash"],
                parent_hash=row["parent_hash"],
                checksum=row["checksum"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
