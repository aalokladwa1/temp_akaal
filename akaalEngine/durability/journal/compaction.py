"""
Journal Compaction & Retention GC Engine for Authority #5 — Durability (DUR-013).

Blocker 2 fixes:
1. compact_journal anchor uses HMAC-SHA256 (not plain SHA-256) with a secret signing key.
   Anyone who can mutate the DB cannot recompute the MAC without the key — forged anchors
   are detected by verify_chain_integrity().
2. purge_expired_records is routed through the same anchor path: if any records survive the
   age-based purge, an authenticated anchor is persisted before deletion so the remaining
   chain can still be verified.
"""

import datetime
import hashlib
import hmac
import sqlite3
from typing import Optional

from akaalEngine.durability.models.errors import JournalCorruptError, DurabilityConfigError
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class JournalCompactionEngine:
    """Executes safe compaction and retention-based garbage collection of operation journals."""

    def __init__(self, backend: SQLiteWalBackend, anchor_key: bytes) -> None:
        if not anchor_key or not isinstance(anchor_key, bytes):
            raise DurabilityConfigError("JournalCompactionEngine requires a non-empty bytes anchor_key.")
        self.backend = backend
        self.anchor_key = anchor_key
        self._ensure_anchor_table()

    def _ensure_anchor_table(self) -> None:
        conn = self.backend._get_connection()
        with self.backend._mutex:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_anchors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    boundary_sequence INTEGER NOT NULL,
                    anchor_parent_hash TEXT NOT NULL,
                    anchor_mac TEXT NOT NULL,
                    compacted_at TEXT NOT NULL
                );
            """)

    def _compute_anchor_mac(self, boundary_sequence: int, anchor_parent_hash: str, compacted_at: str) -> str:
        """Produces an HMAC-SHA256 MAC for an anchor row. Cannot be forged without anchor_key."""
        anchor_data = f"ANCHOR|{boundary_sequence}|{anchor_parent_hash}|{compacted_at}"
        return hmac.new(self.anchor_key, anchor_data.encode("utf-8"), hashlib.sha256).hexdigest()


    def _write_anchor_in_tx(self, conn: sqlite3.Connection, boundary_sequence: int, anchor_parent_hash: str) -> None:
        """Inserts an authenticated anchor row inside the caller's open transaction."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        mac = self._compute_anchor_mac(boundary_sequence, anchor_parent_hash, now)
        conn.execute("""
            INSERT INTO journal_anchors (boundary_sequence, anchor_parent_hash, anchor_mac, compacted_at)
            VALUES (?, ?, ?, ?);
        """, (boundary_sequence, anchor_parent_hash, mac, now))

    def compact_journal(self, safe_sequence_boundary: int) -> int:
        """
        Atomically:
        1. Reads parent_hash from the record AT `safe_sequence_boundary` (the authenticated
           chain link into the deleted prefix).
        2. Writes an HMAC-authenticated anchor row for that boundary.
        3. Deletes records with sequence_number < safe_sequence_boundary.
        """
        conn = self.backend._get_connection()
        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")

                cursor = conn.execute(
                    "SELECT parent_hash FROM journal_records WHERE sequence_number = ?;",
                    (safe_sequence_boundary,)
                )
                row = cursor.fetchone()
                if not row:
                    conn.execute("COMMIT;")
                    return 0

                self._write_anchor_in_tx(conn, safe_sequence_boundary, row["parent_hash"])

                cursor = conn.execute(
                    "DELETE FROM journal_records WHERE sequence_number < ?;",
                    (safe_sequence_boundary,)
                )
                deleted_count = cursor.rowcount
                conn.execute("COMMIT;")
                return deleted_count
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    def purge_expired_records(self, max_age_days: int) -> int:
        """
        Deletes journal records older than max_age_days.

        If records survive the purge, an authenticated anchor is written before deletion
        so the remaining hash-chain can still be verified. If all records are purged,
        no anchor is needed (chain becomes empty).
        """
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)).isoformat()
        conn = self.backend._get_connection()
        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")

                # Find the lowest-sequence record that would survive the purge
                cursor = conn.execute(
                    "SELECT MIN(sequence_number) as min_survive FROM journal_records WHERE created_at >= ?;",
                    (cutoff,)
                )
                row = cursor.fetchone()
                min_surviving_seq = row["min_survive"] if row and row["min_survive"] is not None else None

                if min_surviving_seq is not None:
                    # Some records survive — anchor at the survival boundary before deleting
                    cursor = conn.execute(
                        "SELECT parent_hash FROM journal_records WHERE sequence_number = ?;",
                        (min_surviving_seq,)
                    )
                    boundary_row = cursor.fetchone()
                    if boundary_row:
                        self._write_anchor_in_tx(conn, min_surviving_seq, boundary_row["parent_hash"])

                cursor = conn.execute(
                    "DELETE FROM journal_records WHERE created_at < ?;",
                    (cutoff,)
                )
                deleted_count = cursor.rowcount
                conn.execute("COMMIT;")
                return deleted_count
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    def get_chain_start_parent_hash(self, conn: Optional[sqlite3.Connection] = None) -> tuple:
        """
        Returns (expected_start_sequence, expected_parent_hash) for chain verification.
        If a compaction anchor exists, verifies its HMAC before trusting it.
        Raises JournalCorruptError if the anchor MAC does not match (tampering detected).
        """
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute(
            "SELECT boundary_sequence, anchor_parent_hash, anchor_mac, compacted_at FROM journal_anchors ORDER BY boundary_sequence DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            return (1, "0" * 64)  # Genesis

        # Verify HMAC — detect anchor tampering / recomputed SHA-256 forgery
        expected_mac = self._compute_anchor_mac(
            row["boundary_sequence"], row["anchor_parent_hash"], row["compacted_at"]
        )
        if not hmac.compare_digest(expected_mac, row["anchor_mac"]):
            raise JournalCorruptError(
                f"Journal compaction anchor HMAC mismatch at boundary {row['boundary_sequence']}: "
                f"anchor has been forged or tampered with."
            )

        return (row["boundary_sequence"], row["anchor_parent_hash"])
