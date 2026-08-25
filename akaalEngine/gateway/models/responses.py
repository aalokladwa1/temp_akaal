"""
akaalEngine.gateway.models.responses
====================================
Canonical normalized Gateway response wrapper.
Surfaces execution status, payload, failure categories, and proof metadata while protecting secret boundaries.
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Generic, List, Mapping, Optional, TypeVar

T = TypeVar("T")

def get_receipt_signing_key() -> bytes:
    """Returns the active EngineGateway receipt signing key. Fails closed if secret is unprovisioned or empty."""
    key = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET")
    if not key or not key.strip():
        from akaalEngine.gateway.models.errors import GatewayConfigurationError
        raise GatewayConfigurationError(
            "EngineGateway receipt secret is not provisioned. Production must configure the 'AKAAL_GATEWAY_RECEIPT_SECRET' environment variable."
        )
    return key.strip().encode("utf-8")


def sign_receipt(
    migration_id: str,
    run_id: str,
    operation_id: str,
    fencing_epoch: Optional[int],
    status_code: str,
    initialization_fingerprint: Optional[str] = None,
    job_id: Optional[str] = None,
) -> str:
    """Generates deterministic HMAC-SHA256 signature for engine execution receipt."""
    key = get_receipt_signing_key()
    msg = f"{migration_id}:{run_id}:{operation_id}:{fencing_epoch or 0}:{status_code}:{initialization_fingerprint or ''}:{job_id or ''}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_receipt_signature(receipt: Mapping[str, Any]) -> bool:
    """Verifies that an execution receipt was genuinely signed by EngineGateway."""
    if not isinstance(receipt, Mapping):
        return False
    try:
        expected_sig = sign_receipt(
            migration_id=receipt.get("gateway_migration_id", ""),
            run_id=receipt.get("gateway_run_id", ""),
            operation_id=receipt.get("gateway_operation_id", ""),
            fencing_epoch=receipt.get("gateway_fencing_epoch"),
            status_code=receipt.get("gateway_status_code", ""),
            initialization_fingerprint=receipt.get("initialization_fingerprint", ""),
            job_id=receipt.get("gateway_job_id", ""),
        )
    except Exception:
        # Fails closed if signing key is unprovisioned, invalid, or signing fails
        return False
    sig = receipt.get("receipt_signature") or receipt.get("signature")
    if not sig:
        return False
    return hmac.compare_digest(sig, expected_sig)


@dataclass(frozen=True)
class GatewayResponse(Generic[T]):
    """Normalized response envelope returned by EngineGateway for all operations."""
    operation_id: str
    operation_type: str
    migration_id: str
    run_id: str
    success: bool
    status_code: str
    payload: Optional[T] = None
    failure_category: Optional[str] = None
    error_message: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    retryable: bool = False
    terminal: bool = True
    fencing_epoch: Optional[int] = None
    executed_at: float = field(default_factory=time.time)
    proof_classification: Optional[str] = None
    execution_receipt: Optional[Mapping[str, Any]] = None

    @classmethod
    def create_success(
        cls,
        operation_id: str,
        operation_type: str,
        migration_id: str,
        run_id: str,
        payload: T,
        fencing_epoch: Optional[int] = None,
        proof_classification: Optional[str] = None,
        job_id: Optional[str] = None,
        initialization_fingerprint: Optional[str] = None,
    ) -> "GatewayResponse[T]":
        """Constructs a successful GatewayResponse with authenticated execution receipt."""
        now = time.time()
        effective_job_id = job_id or operation_id
        sig = sign_receipt(
            migration_id=migration_id,
            run_id=run_id,
            operation_id=operation_id,
            fencing_epoch=fencing_epoch,
            status_code="SUCCESS",
            initialization_fingerprint=initialization_fingerprint,
            job_id=effective_job_id,
        )
        rcpt = {
            "engine_signer": "akaalEngineGateway-v1",
            "gateway_operation_id": operation_id,
            "gateway_operation_type": operation_type,
            "gateway_migration_id": migration_id,
            "gateway_run_id": run_id,
            "gateway_job_id": effective_job_id,
            "gateway_fencing_epoch": fencing_epoch,
            "initialization_fingerprint": initialization_fingerprint or "",
            "gateway_status_code": "SUCCESS",
            "receipt_signature": sig,
            "proof_classification": proof_classification or "ENGINE_PROVEN",
            "executed_at": now,
        }
        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            migration_id=migration_id,
            run_id=run_id,
            success=True,
            status_code="SUCCESS",
            payload=payload,
            fencing_epoch=fencing_epoch,
            executed_at=now,
            proof_classification=proof_classification,
            execution_receipt=rcpt,
        )

    @classmethod
    def create_failure(
        cls,
        operation_id: str,
        operation_type: str,
        migration_id: str,
        run_id: str,
        failure_category: str,
        error_message: str,
        reasons: Optional[List[str]] = None,
        retryable: bool = False,
        terminal: bool = True,
        fencing_epoch: Optional[int] = None,
        job_id: Optional[str] = None,
        initialization_fingerprint: Optional[str] = None,
    ) -> "GatewayResponse[T]":
        """Constructs a failed GatewayResponse with authenticated failure execution receipt."""
        now = time.time()
        effective_job_id = job_id or operation_id
        rcpt: Optional[dict[str, Any]] = None
        try:
            sig = sign_receipt(
                migration_id=migration_id,
                run_id=run_id,
                operation_id=operation_id,
                fencing_epoch=fencing_epoch,
                status_code=failure_category,
                initialization_fingerprint=initialization_fingerprint,
                job_id=effective_job_id,
            )
            rcpt = {
                "engine_signer": "akaalEngineGateway-v1",
                "gateway_operation_id": operation_id,
                "gateway_operation_type": operation_type,
                "gateway_migration_id": migration_id,
                "gateway_run_id": run_id,
                "gateway_job_id": effective_job_id,
                "gateway_fencing_epoch": fencing_epoch,
                "initialization_fingerprint": initialization_fingerprint or "",
                "gateway_status_code": failure_category,
                "receipt_signature": sig,
                "proof_classification": "FAILURE_PROVEN",
                "executed_at": now,
            }
        except Exception:
            # If receipt signing fails (e.g. missing secret), omit receipt to avoid cascade crash.
            # Do NOT forge a fake signature or unsigned receipt dictionary.
            rcpt = None

        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            migration_id=migration_id,
            run_id=run_id,
            success=False,
            status_code=failure_category,
            failure_category=failure_category,
            error_message=error_message,
            reasons=reasons or [],
            retryable=retryable,
            terminal=terminal,
            fencing_epoch=fencing_epoch,
            executed_at=now,
            proof_classification="FAILURE_PROVEN" if rcpt is not None else None,
            execution_receipt=rcpt,
        )
