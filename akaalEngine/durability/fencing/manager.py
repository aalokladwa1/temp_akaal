"""
Lease Epoch & Fencing Token Manager for Authority #5 — Durability (DUR-006).
"""

import datetime
import hashlib
import hmac
from typing import Optional
from akaalEngine.durability.models.fencing import FencingToken, LeaseEpoch
from akaalEngine.durability.models.errors import StaleGenerationError, FencingViolationError, DurabilityError, DurabilityConfigError
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class FencingTokenManager:
    """Manages monotonic generation epoch issuance and token validation."""

    def __init__(self, backend: SQLiteWalBackend, signing_key: bytes) -> None:
        if not signing_key or not isinstance(signing_key, bytes):
            raise DurabilityConfigError("FencingTokenManager requires a non-empty bytes signing_key.")
        self.backend = backend
        self.signing_key = signing_key

    def issue_token(self, resource_id: str, worker_id: str) -> FencingToken:
        """Issues a new fencing token for a resource, incrementing the resource epoch monotonically."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = self.backend._get_connection()

        with self.backend._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")
                cursor = conn.execute("SELECT current_epoch FROM fencing_tokens WHERE resource_id = ?;", (resource_id,))
                row = cursor.fetchone()
                new_epoch = (row["current_epoch"] if row else 0) + 1

                if row:
                    conn.execute(
                        "UPDATE fencing_tokens SET current_epoch = ?, last_worker_id = ?, updated_at = ? WHERE resource_id = ?;",
                        (new_epoch, worker_id, now, resource_id)
                    )
                else:
                    conn.execute(
                        "INSERT INTO fencing_tokens (resource_id, current_epoch, last_worker_id, updated_at) VALUES (?, ?, ?, ?);",
                        (resource_id, new_epoch, worker_id, now)
                    )
                conn.execute("COMMIT;")

                token_data = f"{resource_id}|{worker_id}|{new_epoch}|{now}"
                sig = hmac.new(self.signing_key, token_data.encode("utf-8"), hashlib.sha256).hexdigest()

                return FencingToken(
                    resource_id=resource_id,
                    worker_id=worker_id,
                    fencing_epoch=new_epoch,
                    issued_at=now,
                    signature=sig,
                )
            except Exception as e:
                conn.execute("ROLLBACK;")
                raise e

    def validate_token(self, token: FencingToken) -> bool:
        """Validates that token signature is authentic and epoch is current."""
        self._verify_hmac(token)
        conn = self.backend._get_connection()
        cursor = conn.execute("SELECT current_epoch FROM fencing_tokens WHERE resource_id = ?;", (token.resource_id,))
        row = cursor.fetchone()
        if not row:
            return True
        curr_epoch = row["current_epoch"]
        if token.fencing_epoch < curr_epoch:
            raise StaleGenerationError(f"Stale fencing token: token epoch {token.fencing_epoch} is lower than current resource epoch {curr_epoch}.")
        return True

    def validate_token_in_tx(self, token: FencingToken, conn: "sqlite3.Connection") -> None:
        """
        Validates HMAC authenticity then asserts exact epoch equality against the live
        fencing_tokens row, all within the caller's open transaction.

        Raises:
            FencingViolationError: HMAC signature is invalid.
            StaleGenerationError: token epoch != current resource epoch (stale or fabricated).
        """
        import sqlite3 as _sqlite3
        self._verify_hmac(token)
        cursor = conn.execute(
            "SELECT current_epoch FROM fencing_tokens WHERE resource_id = ?;",
            (token.resource_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise FencingViolationError(
                f"Fencing violation: no fencing token has been issued for resource '{token.resource_id}'."
            )
        current_epoch = row["current_epoch"]
        if token.fencing_epoch != current_epoch:
            raise StaleGenerationError(
                f"Fencing violation: token epoch {token.fencing_epoch} != current resource epoch {current_epoch} "
                f"for resource '{token.resource_id}'. Token must be the most recently issued one."
            )

    def _verify_hmac(self, token: FencingToken) -> None:
        """Verifies token HMAC signature. Raises FencingViolationError on mismatch."""
        token_data = f"{token.resource_id}|{token.worker_id}|{token.fencing_epoch}|{token.issued_at}"
        expected_sig = hmac.new(self.signing_key, token_data.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(token.signature, expected_sig):
            raise FencingViolationError("Fencing token HMAC signature verification failed.")

