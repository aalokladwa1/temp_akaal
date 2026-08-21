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
        expected_invocation_id: Optional[str] = None,
        expected_attempt_id: Optional[str] = None,
        expected_lease_id: Optional[str] = None,
        expected_graph_node_id: Optional[str] = None,
        expected_binding_id: Optional[str] = None,
        expected_contract_version: Optional[str] = None,
    ) -> Mapping[str, Any]:
        """Reconciles result proposal. Throws StaleResultError on lease/epoch/fingerprint mismatch."""
        if not isinstance(result, EngineInvocationResult):
            raise StaleResultError(f"Result rejected: Invalid result object type {type(result).__name__}.")

        if expected_attempt_id and result.attempt_id != expected_attempt_id:
            raise StaleResultError(
                f"Result rejected: Attempt ID mismatch: expected {expected_attempt_id!r} != result {result.attempt_id!r}."
            )

        if expected_invocation_id and result.invocation_id != expected_invocation_id:
            raise StaleResultError(
                f"Result rejected: Invocation ID mismatch for attempt {result.attempt_id!r}: expected {expected_invocation_id!r} != result {result.invocation_id!r}."
            )

        if expected_graph_node_id and result.graph_node_id != expected_graph_node_id:
            raise StaleResultError(
                f"Result rejected: Graph node ID mismatch for attempt {result.attempt_id!r}: expected {expected_graph_node_id!r} != result {result.graph_node_id!r}."
            )

        lease = self.lease_manager.get_lease(result.attempt_id, conn)
        if lease is None:
            raise StaleResultError(f"Result rejected: No active lease found for attempt {result.attempt_id!r}.")

        if expected_lease_id and result.lease_id != expected_lease_id:
            raise StaleResultError(
                f"Result rejected: Lease ID mismatch for attempt {result.attempt_id!r}: expected {expected_lease_id!r} != result {result.lease_id!r}."
            )


        if lease.lease_id != result.lease_id:
            raise StaleResultError(
                f"Result rejected: Lease ID mismatch for attempt {result.attempt_id!r}: current stored {lease.lease_id!r} != result {result.lease_id!r}."
            )

        if lease.fence_epoch != result.fence_epoch:
            raise StaleResultError(
                f"Result rejected: Fence epoch mismatch for attempt {result.attempt_id!r}: current stored epoch {lease.fence_epoch} != result epoch {result.fence_epoch}."
            )

        if not result.initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Missing initialization fingerprint on result for attempt {result.attempt_id!r}."
            )

        if result.initialization_fingerprint != lease.initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Result initialization fingerprint {result.initialization_fingerprint!r} != stored lease fingerprint {lease.initialization_fingerprint!r}."
            )

        if lease.initialization_fingerprint != expected_initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Initialization fingerprint mismatch: stored {lease.initialization_fingerprint!r} != expected {expected_initialization_fingerprint!r}."
            )

        if expected_binding_id is not None:
            if not result.binding_id:
                raise StaleResultError(
                    f"Result rejected: Missing binding_id on result for attempt {result.attempt_id!r}."
                )
            if result.binding_id != expected_binding_id:
                raise StaleResultError(
                    f"Result rejected: Binding ID mismatch for attempt {result.attempt_id!r}: expected {expected_binding_id!r} != result {result.binding_id!r}."
                )

        if expected_contract_version is not None:
            if not result.contract_version:
                raise StaleResultError(
                    f"Result rejected: Missing contract_version on result for attempt {result.attempt_id!r}."
                )
            if result.contract_version != expected_contract_version:
                raise StaleResultError(
                    f"Result rejected: Contract version mismatch for attempt {result.attempt_id!r}: expected {expected_contract_version!r} != result {result.contract_version!r}."
                )

        if not isinstance(result.result_payload, Mapping):

            raise StaleResultError(
                f"Result rejected: Malformed result_payload type {type(result.result_payload).__name__} for attempt {result.attempt_id!r}."
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
