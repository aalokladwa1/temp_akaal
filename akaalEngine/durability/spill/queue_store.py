"""
Durable Queue Storage Primitives for Authority #5 — Durability (DUR-010).
"""

import datetime
import sqlite3
import uuid
from typing import Optional, List
from akaalEngine.durability.models.queue import QueueMessageRef
from akaalEngine.durability.models.errors import FencingViolationError, DurabilityError
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class DurableQueueStore:
    """Provides storage-level queue primitives: enqueue, atomic claim lease, ACK, and expiration cleanup."""

    def __init__(self, backend: SQLiteWalBackend) -> None:
        self.backend = backend

    def store_message(self, queue_name: str, payload: bytes, conn: Optional[sqlite3.Connection] = None) -> str:
        """Stores a durable queue message after validating quota and sanitization."""
        self.backend.validate_quota(len(payload))
        msg_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute("SELECT MAX(sequence_number) as max_seq FROM queue_records WHERE queue_name = ?;", (queue_name,))
                row = cursor.fetchone()
                seq = (row["max_seq"] or 0) + 1 if row and row["max_seq"] is not None else 1

                use_conn.execute("""
                    INSERT INTO queue_records (message_id, queue_name, sequence_number, payload, claimed_by, claim_id, lease_expires_at, attempt_count, created_at)
                    VALUES (?, ?, ?, ?, NULL, NULL, NULL, 0, ?);
                """, (msg_id, queue_name, seq, payload, now))
                if own_tx:
                    use_conn.execute("COMMIT;")
                return msg_id
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                raise e

    def claim_message(self, queue_name: str, worker_id: str, lease_duration_sec: int, conn: Optional[sqlite3.Connection] = None) -> Optional[QueueMessageRef]:
        """Atomically claims an available queue message issuing a unique claim_id."""
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_str = now_dt.isoformat()
        lease_expires_str = (now_dt + datetime.timedelta(seconds=lease_duration_sec)).isoformat()
        claim_id = str(uuid.uuid4())
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute("""
                    SELECT message_id, sequence_number, payload, attempt_count, created_at
                    FROM queue_records
                    WHERE queue_name = ? AND (claimed_by IS NULL OR lease_expires_at < ?)
                    ORDER BY sequence_number ASC LIMIT 1;
                """, (queue_name, now_str))
                row = cursor.fetchone()
                if not row:
                    if own_tx:
                        use_conn.execute("COMMIT;")
                    return None

                msg_id = row["message_id"]
                new_attempts = row["attempt_count"] + 1

                use_conn.execute("""
                    UPDATE queue_records SET
                        claimed_by = ?,
                        claim_id = ?,
                        lease_expires_at = ?,
                        attempt_count = ?
                    WHERE message_id = ?;
                """, (worker_id, claim_id, lease_expires_str, new_attempts, msg_id))

                if own_tx:
                    use_conn.execute("COMMIT;")
                return QueueMessageRef(
                    message_id=msg_id,
                    queue_name=queue_name,
                    sequence_number=row["sequence_number"],
                    payload=row["payload"],
                    claimed_by=worker_id,
                    claim_id=claim_id,
                    lease_expires_at=lease_expires_str,
                    attempt_count=new_attempts,
                    created_at=row["created_at"],
                )
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                raise e

    def ack_message(self, message_id: str, claimed_by: str, claim_id: str, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Acknowledges and removes a processed queue message.
        Defect #1: Requires BOTH claimed_by AND claim_id. Ownerless ACK is REMOVED!
        """
        if not claimed_by or not claim_id:
            raise FencingViolationError("Queue ACK requires both claimed_by and claim_id.")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                cursor = use_conn.execute(
                    "DELETE FROM queue_records WHERE message_id = ? AND claimed_by = ? AND claim_id = ? AND lease_expires_at >= ?;",
                    (message_id, claimed_by, claim_id, now_str)
                )

                if cursor.rowcount == 0:
                    raise FencingViolationError(
                        f"Stale or invalid ACK rejected: message '{message_id}' is not active for worker '{claimed_by}' with claim_id '{claim_id}'."
                    )

                if own_tx:
                    use_conn.execute("COMMIT;")
                return True
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise e
