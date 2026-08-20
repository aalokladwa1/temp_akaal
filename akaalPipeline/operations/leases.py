"""akaalPipeline.operations.leases
=================================
Durable execution attempt lease & monotonic fence epoch manager.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from akaalPipeline.contracts.errors import LeaseConflictError, UnableToAcquireLeaseError


@dataclass(frozen=True)
class ExecutionLease:
    lease_id: str
    attempt_id: str
    owner_id: str
    fence_epoch: int
    issued_at: str
    expires_at: str
    renewed_at: str
    initialization_fingerprint: str

    def is_expired(self, current_time_iso: Optional[str] = None) -> bool:
        now = current_time_iso or datetime.now(timezone.utc).isoformat()
        return now > self.expires_at


class LeaseManager:
    def acquire_lease(
        self,
        lease_id: str,
        attempt_id: str,
        owner_id: str,
        expires_at: str,
        initialization_fingerprint: str,
        conn: sqlite3.Connection,
    ) -> ExecutionLease:
        """Acquire or renew an execution lease with monotonic fence epoch increment."""
        cur = conn.execute(
            "SELECT lease_id, owner_id, fence_epoch, expires_at FROM leases WHERE attempt_id = ?",
            (attempt_id,),
        )
        row = cur.fetchone()
        now = datetime.now(timezone.utc).isoformat()

        if row is not None:
            existing_owner = row["owner_id"]
            existing_expires = row["expires_at"]
            existing_epoch = row["fence_epoch"]

            # If unexpired lease held by another owner -> fail to acquire
            if existing_owner != owner_id and now <= existing_expires:
                raise UnableToAcquireLeaseError(
                    f"Attempt {attempt_id!r} is currently leased to active owner {existing_owner!r} until {existing_expires}"
                )

            new_epoch = existing_epoch + 1
            conn.execute(
                """
                UPDATE leases SET
                    lease_id = ?, owner_id = ?, fence_epoch = ?, issued_at = ?,
                    expires_at = ?, renewed_at = ?, initialization_fingerprint = ?
                WHERE attempt_id = ? AND fence_epoch = ?
                """,
                (lease_id, owner_id, new_epoch, now, expires_at, now, initialization_fingerprint, attempt_id, existing_epoch),
            )
            return ExecutionLease(
                lease_id=lease_id,
                attempt_id=attempt_id,
                owner_id=owner_id,
                fence_epoch=new_epoch,
                issued_at=now,
                expires_at=expires_at,
                renewed_at=now,
                initialization_fingerprint=initialization_fingerprint,
            )
        else:
            new_epoch = 1
            conn.execute(
                """
                INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (lease_id, attempt_id, owner_id, new_epoch, now, expires_at, now, initialization_fingerprint),
            )
            return ExecutionLease(
                lease_id=lease_id,
                attempt_id=attempt_id,
                owner_id=owner_id,
                fence_epoch=new_epoch,
                issued_at=now,
                expires_at=expires_at,
                renewed_at=now,
                initialization_fingerprint=initialization_fingerprint,
            )

    def validate_lease(self, attempt_id: str, lease_id: str, fence_epoch: int, conn: sqlite3.Connection) -> ExecutionLease:
        """Validate lease identity and fence epoch. Fails closed on stale lease or epoch mismatch."""
        cur = conn.execute("SELECT * FROM leases WHERE attempt_id = ?", (attempt_id,))
        row = cur.fetchone()
        if row is None:
            raise LeaseConflictError(f"No active lease found for attempt {attempt_id!r}")
        if row["lease_id"] != lease_id:
            raise LeaseConflictError(f"Lease ID mismatch for attempt {attempt_id!r}: expected {row['lease_id']!r}, got {lease_id!r}")
        if row["fence_epoch"] != fence_epoch:
            raise LeaseConflictError(
                f"Fence epoch mismatch for attempt {attempt_id!r}: current stored epoch {row['fence_epoch']} != caller epoch {fence_epoch}"
            )
        return ExecutionLease(
            lease_id=row["lease_id"],
            attempt_id=row["attempt_id"],
            owner_id=row["owner_id"],
            fence_epoch=row["fence_epoch"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            renewed_at=row["renewed_at"],
            initialization_fingerprint=row["initialization_fingerprint"],
        )

    def get_lease(self, attempt_id: str, conn: sqlite3.Connection) -> Optional[ExecutionLease]:
        cur = conn.execute("SELECT * FROM leases WHERE attempt_id = ?", (attempt_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ExecutionLease(
            lease_id=row["lease_id"],
            attempt_id=row["attempt_id"],
            owner_id=row["owner_id"],
            fence_epoch=row["fence_epoch"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            renewed_at=row["renewed_at"],
            initialization_fingerprint=row["initialization_fingerprint"],
        )
