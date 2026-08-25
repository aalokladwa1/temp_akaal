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
        expected_migration_id: Optional[str] = None,
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

        receipt = result.result_payload.get("engine_execution_receipt") or result.result_payload.get("execution_receipt")
        if not receipt or not isinstance(receipt, dict):
            raise StaleResultError(
                f"Result rejected: Missing authoritative Engine execution receipt in result_payload for attempt {result.attempt_id!r}."
            )

        rcpt_run = receipt.get("gateway_run_id") or receipt.get("run_id")
        if not rcpt_run or rcpt_run != result.attempt_id:
            raise StaleResultError(
                f"Result rejected: Execution receipt run ID mismatch: receipt {rcpt_run!r} != attempt {result.attempt_id!r}."
            )

        rcpt_epoch = receipt.get("gateway_fencing_epoch") if "gateway_fencing_epoch" in receipt else receipt.get("fencing_epoch")
        if rcpt_epoch is None or rcpt_epoch != result.fence_epoch:
            raise StaleResultError(
                f"Result rejected: Execution receipt fencing epoch mismatch: receipt {rcpt_epoch} != fence epoch {result.fence_epoch}."
            )

        rcpt_mig = receipt.get("gateway_migration_id") or receipt.get("migration_id")
        if not rcpt_mig:
            raise StaleResultError(
                f"Result rejected: Missing gateway_migration_id in execution receipt for attempt {result.attempt_id!r}."
            )
        if expected_migration_id and rcpt_mig != expected_migration_id:
            raise StaleResultError(
                f"Result rejected: Execution receipt migration ID mismatch: receipt {rcpt_mig!r} != expected migration {expected_migration_id!r}."
            )
        if result.result_payload.get("migration_id") and rcpt_mig != result.result_payload.get("migration_id"):
            raise StaleResultError(
                f"Result rejected: Execution receipt migration ID mismatch: receipt {rcpt_mig!r} != payload {result.result_payload.get('migration_id')!r}."
            )

        rcpt_node = receipt.get("gateway_job_id") or receipt.get("graph_node_id") or receipt.get("job_id")
        if result.graph_node_id and (not rcpt_node or rcpt_node != result.graph_node_id):
            raise StaleResultError(
                f"Result rejected: Execution receipt node ID mismatch: receipt {rcpt_node!r} != node {result.graph_node_id!r}."
            )

        rcpt_fp = receipt.get("initialization_fingerprint") or receipt.get("fingerprint")
        if not rcpt_fp or rcpt_fp != expected_initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Execution receipt fingerprint mismatch: receipt {rcpt_fp!r} != expected fp {expected_initialization_fingerprint!r}."
            )
        if result.initialization_fingerprint and rcpt_fp != result.initialization_fingerprint:
            raise StaleResultError(
                f"Result rejected: Execution receipt fingerprint mismatch: receipt {rcpt_fp!r} != result fp {result.initialization_fingerprint!r}."
            )

        rcpt_status = receipt.get("gateway_status_code") or receipt.get("status_code") or receipt.get("status")
        if not rcpt_status:
            raise StaleResultError(
                f"Result rejected: Missing gateway_status_code in execution receipt for attempt {result.attempt_id!r}."
            )
        if result.is_success and rcpt_status != "SUCCESS":
            raise StaleResultError(
                f"Result rejected: Execution receipt status mismatch: receipt {rcpt_status!r} != SUCCESS."
            )

        rcpt_sig = receipt.get("receipt_signature") or receipt.get("signature")
        if not rcpt_sig:
            raise StaleResultError(
                f"Result rejected: Missing required cryptographic receipt_signature in execution receipt for attempt {result.attempt_id!r}."
            )
        from akaalPipeline.security.receipts import verify_execution_receipt
        if not verify_execution_receipt(receipt):
            raise StaleResultError(
                f"Result rejected: Cryptographic signature on Engine execution receipt is invalid or forged for attempt {result.attempt_id!r}."
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
