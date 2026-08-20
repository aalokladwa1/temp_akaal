"""akaalPipeline.recovery.checkpoints
====================================
Validates and records durable checkpoints.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from akaalPipeline.contracts.errors import CheckpointRejectedError
from akaalPipeline.operations.leases import LeaseManager


@dataclass(frozen=True)
class CheckpointCandidate:
    checkpoint_id: str
    attempt_id: str
    engine_invocation_id: str
    lease_id: str
    fence_epoch: int
    graph_node_id: str
    initialization_fingerprint: str
    engine_binding: str
    checkpoint_payload_reference: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CheckpointManager:
    def __init__(self, lease_manager: LeaseManager) -> None:
        self.lease_manager = lease_manager

    def record_checkpoint(
        self,
        candidate: CheckpointCandidate,
        expected_initialization_fingerprint: str,
        conn: sqlite3.Connection,
    ) -> None:
        """Validates candidate against stored attempt lease, fence epoch, and initialization fingerprint. Fails closed on mismatch."""
        lease = self.lease_manager.get_lease(candidate.attempt_id, conn)
        if lease is None:
            raise CheckpointRejectedError(f"Checkpoint rejected: No active lease for attempt {candidate.attempt_id!r}.")

        if lease.lease_id != candidate.lease_id:
            raise CheckpointRejectedError(
                f"Checkpoint rejected: Lease ID mismatch for attempt {candidate.attempt_id!r}: current stored {lease.lease_id!r} != candidate {candidate.lease_id!r}."
            )

        if lease.fence_epoch != candidate.fence_epoch:
            raise CheckpointRejectedError(
                f"Checkpoint rejected: Fence epoch mismatch for attempt {candidate.attempt_id!r}: current stored epoch {lease.fence_epoch} != candidate epoch {candidate.fence_epoch}."
            )

        if candidate.initialization_fingerprint != lease.initialization_fingerprint:
            raise CheckpointRejectedError(
                f"Checkpoint rejected: Candidate initialization fingerprint {candidate.initialization_fingerprint!r} != active lease fingerprint {lease.initialization_fingerprint!r}."
            )

        if lease.initialization_fingerprint != expected_initialization_fingerprint:
            raise CheckpointRejectedError(
                f"Checkpoint rejected: Stored lease initialization fingerprint {lease.initialization_fingerprint!r} != expected argument fingerprint {expected_initialization_fingerprint!r}."
            )

        if candidate.initialization_fingerprint != expected_initialization_fingerprint:
            raise CheckpointRejectedError(
                f"Checkpoint rejected: Candidate initialization fingerprint {candidate.initialization_fingerprint!r} != expected argument fingerprint {expected_initialization_fingerprint!r}."
            )

        # Check for duplicate checkpoint ID and verify full canonical identity/provenance tuple
        cur = conn.execute(
            """
            SELECT attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id,
                   initialization_fingerprint, binding_id, payload_reference
            FROM checkpoints WHERE checkpoint_id = ?
            """,
            (candidate.checkpoint_id,),
        )
        row = cur.fetchone()
        if row is not None:
            if (
                row["attempt_id"] != candidate.attempt_id
                or row["invocation_id"] != candidate.engine_invocation_id
                or row["lease_id"] != candidate.lease_id
                or row["fence_epoch"] != candidate.fence_epoch
                or row["graph_node_id"] != candidate.graph_node_id
                or row["initialization_fingerprint"] != candidate.initialization_fingerprint
                or row["binding_id"] != candidate.engine_binding
                or row["payload_reference"] != candidate.checkpoint_payload_reference
            ):
                raise CheckpointRejectedError(
                    f"Checkpoint rejected: Duplicate checkpoint ID {candidate.checkpoint_id!r} with conflicting canonical content/provenance."
                )
            return  # Idempotent replay accepted for identical content


        conn.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch,
                graph_node_id, initialization_fingerprint, binding_id,
                payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.checkpoint_id,
                candidate.attempt_id,
                candidate.engine_invocation_id,
                candidate.lease_id,
                candidate.fence_epoch,
                candidate.graph_node_id,
                candidate.initialization_fingerprint,
                candidate.engine_binding,
                candidate.checkpoint_payload_reference,
                candidate.created_at,
            ),
        )
