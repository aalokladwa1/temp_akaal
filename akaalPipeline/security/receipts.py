"""
akaalPipeline.security.receipts
===============================
Boundary-neutral verification of Engine execution receipts.
Computes and verifies HMAC-SHA256 signatures adhering to the AKAAL Engine Execution Receipt specification
without coupling Pipeline to Engine internal modules.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Mapping, Optional

def get_receipt_verification_key() -> bytes:
    """Returns the active receipt verification secret key. Fails closed if secret is unprovisioned."""
    key = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET")
    if not key:
        raise ValueError(
            "Receipt verification secret is not provisioned. Production must configure the 'AKAAL_GATEWAY_RECEIPT_SECRET' environment variable."
        )
    return key.encode("utf-8")


def verify_execution_receipt(receipt: Mapping[str, Any], secret_key: Optional[bytes] = None) -> bool:
    """
    Verifies that an execution receipt was genuinely signed according to the canonical specification.
    Fails closed if the secret key is unprovisioned or invalid.
    """
    if not isinstance(receipt, Mapping):
        return False
    try:
        key = secret_key or get_receipt_verification_key()
    except Exception:
        return False

    migration_id = str(receipt.get("gateway_migration_id", ""))
    run_id = str(receipt.get("gateway_run_id", ""))
    operation_id = str(receipt.get("gateway_operation_id", ""))
    fencing_epoch = receipt.get("gateway_fencing_epoch")
    status_code = str(receipt.get("gateway_status_code", ""))
    initialization_fingerprint = str(receipt.get("initialization_fingerprint", ""))
    job_id = str(receipt.get("gateway_job_id", ""))

    msg = f"{migration_id}:{run_id}:{operation_id}:{fencing_epoch or 0}:{status_code}:{initialization_fingerprint}:{job_id}".encode("utf-8")
    expected_sig = hmac.new(key, msg, hashlib.sha256).hexdigest()

    sig = receipt.get("receipt_signature") or receipt.get("signature")
    if not sig or not isinstance(sig, str):
        return False
    return hmac.compare_digest(sig, expected_sig)
