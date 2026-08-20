"""akaalPipeline.execution.result_reconciliation
==================================================
Reconciles engine result proposals against active attempt lease, fence epoch, and initialization fingerprint.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Mapping
from akaalPipeline.contracts.errors import StaleResultError
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.ports.engine import EngineInvocationResult


class ResultReconciler:
    def __init__(self, lease_manager: LeaseManager) -> None:
        self.lease_manager = lease_manager

    def reconcile_result(
        self,
        result: EngineInvocationResult,
        expected_initialization_fingerprint: str,
        conn: sqlite3.Connection,
    ) -> Mapping[str, Any]:
        """Reconciles result proposal. Throws StaleResultError on lease/epoch/fingerprint mismatch."""
        lease = self.lease_manager.get_lease(result.attempt_id, conn)
        if lease is None:
            raise StaleResultError(f"Result rejected: No active lease found for attempt {result.attempt_id!r}.")

        if lease.lease_id != result.lease_id:
            raise StaleResultError(
                f"Result rejected: Lease ID mismatch for attempt {result.attempt_id!r}: current stored {lease.lease_id!r} != result {result.lease_id!r}."
            )

        if lease.fence_epoch != result.fence_epoch:
            raise StaleResultError(
                f"Result rejected: Fence epoch mismatch for attempt {result.attempt_id!r}: current stored epoch {lease.fence_epoch} != result epoch {result.fence_epoch}."
            )

        if result.initialization_fingerprint is not None and result.initialization_fingerprint != lease.initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Result initialization fingerprint {result.initialization_fingerprint!r} != stored lease fingerprint {lease.initialization_fingerprint!r}."
            )

        if lease.initialization_fingerprint != expected_initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Initialization fingerprint mismatch: stored {lease.initialization_fingerprint!r} != expected {expected_initialization_fingerprint!r}."
            )


        if not result.is_success:
            return {
                "status": "FAILED",
                "error_code": result.error_code or "ENGINE_ERROR",
                "error_message": result.error_message or "Physical engine task failed.",
            }

        return {
            "status": "SUCCEEDED",
            "result_payload": result.result_payload,
        }
