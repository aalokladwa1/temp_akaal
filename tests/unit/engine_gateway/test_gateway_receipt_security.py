"""
akaalEngine Gateway Receipt Security & Missing Secret Test Suite
================================================================
Rigorously tests all receipt signing, verification, and missing-secret fail-closed paths.
"""

import os
import pytest
from typing import Any, Dict

from akaalEngine.gateway.models.errors import (
    GatewayError,
    GatewayConfigurationError,
    GatewaySecurityError,
    GatewayAdmissionError,
)
from akaalEngine.gateway.models.responses import (
    GatewayResponse,
    get_receipt_signing_key,
    sign_receipt,
    verify_receipt_signature,
)
from akaalEngine.gateway.failure.translator import FailureTranslator
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.api import EngineGateway


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment around secret tests."""
    original_secret = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET")
    yield
    if original_secret is not None:
        os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = original_secret
    else:
        os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)


def test_receipt_key_present_signed_success_response():
    """receipt key present -> valid signed success response."""
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = "test-secret-key-12345"

    resp = GatewayResponse.create_success(
        operation_id="op-succ-001",
        operation_type="TEST_OPERATION",
        migration_id="mig-001",
        run_id="run-001",
        payload={"data": "sample"},
        fencing_epoch=1,
        job_id="job-001",
        initialization_fingerprint="fp-001",
    )
    assert resp.success is True
    assert resp.execution_receipt is not None
    assert resp.execution_receipt["receipt_signature"] is not None
    assert verify_receipt_signature(resp.execution_receipt) is True


def test_receipt_key_present_signed_failure_response():
    """receipt key present -> valid signed failure response."""
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = "test-secret-key-12345"

    resp = GatewayResponse.create_failure(
        operation_id="op-fail-001",
        operation_type="TEST_OPERATION",
        migration_id="mig-001",
        run_id="run-001",
        failure_category=GatewayFailureCategory.PERMISSION_FAILURE.value,
        error_message="Access denied",
        fencing_epoch=1,
        job_id="job-001",
        initialization_fingerprint="fp-001",
    )
    assert resp.success is False
    assert resp.status_code == GatewayFailureCategory.PERMISSION_FAILURE.value
    assert resp.execution_receipt is not None
    assert resp.execution_receipt["receipt_signature"] is not None
    assert verify_receipt_signature(resp.execution_receipt) is True


def test_receipt_key_absent_success_construction_fails_closed():
    """receipt key absent during success construction -> controlled fail-closed behavior, raises GatewayConfigurationError, never ModuleNotFoundError."""
    os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)

    with pytest.raises(GatewayConfigurationError) as exc_info:
        GatewayResponse.create_success(
            operation_id="op-succ-002",
            operation_type="TEST_OPERATION",
            migration_id="mig-001",
            run_id="run-001",
            payload={"data": "sample"},
        )
    assert "EngineGateway receipt secret is not provisioned" in str(exc_info.value)
    assert isinstance(exc_info.value, GatewayError)


def test_receipt_key_absent_failure_construction_no_cascade():
    """receipt key absent during failure construction -> controlled behavior without recursive/secondary exception cascade."""
    os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)

    # create_failure must NOT raise secondary exception; it returns GatewayResponse with execution_receipt=None
    resp = GatewayResponse.create_failure(
        operation_id="op-fail-002",
        operation_type="TEST_OPERATION",
        migration_id="mig-001",
        run_id="run-001",
        failure_category=GatewayFailureCategory.INTERNAL_ENGINE_FAILURE.value,
        error_message="Primary error occurred",
    )
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.INTERNAL_ENGINE_FAILURE.value
    assert resp.error_message == "Primary error occurred"
    assert resp.execution_receipt is None
    assert resp.proof_classification is None


def test_failure_translator_does_not_crash_when_secret_absent():
    """FailureTranslator cannot crash while attempting to represent original failure when secret is absent."""
    os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)

    ctx = GatewayRequestContext(
        migration_id="mig-001",
        run_id="run-001",
        job_id="job-001",
        operation_id="op-001",
    )

    original_exc = ValueError("Invalid parameter value provided by user")
    resp = FailureTranslator.translate_exception(original_exc, ctx, "TEST_OP")
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.INVALID_REQUEST.value
    assert "Invalid parameter value" in resp.error_message


def test_empty_and_whitespace_receipt_secret_fails_closed():
    """invalid/empty/whitespace receipt secret fails closed."""
    for empty_val in ["", "   ", "\t\n  "]:
        os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = empty_val
        with pytest.raises(GatewayConfigurationError):
            get_receipt_signing_key()


def test_receipt_verification_integrity():
    """receipt verification remains intact: verifies valid receipts, rejects tampered receipts, fails closed on missing secret."""
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = "test-secret-key-12345"

    resp = GatewayResponse.create_success(
        operation_id="op-succ-003",
        operation_type="TEST_OPERATION",
        migration_id="mig-001",
        run_id="run-001",
        payload={},
        fencing_epoch=2,
    )
    assert verify_receipt_signature(resp.execution_receipt) is True

    # Tampered receipt must fail verification
    tampered_receipt = dict(resp.execution_receipt)
    tampered_receipt["gateway_migration_id"] = "mig-tampered"
    assert verify_receipt_signature(tampered_receipt) is False

    # Corrupt signature must fail verification
    tampered_sig_receipt = dict(resp.execution_receipt)
    tampered_sig_receipt["receipt_signature"] = "0" * 64
    assert verify_receipt_signature(tampered_sig_receipt) is False

    # Missing secret during verification fails closed (returns False, never crashes)
    os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)
    assert verify_receipt_signature(resp.execution_receipt) is False


def test_no_secret_value_appears_in_repr_or_errors():
    """no secret value appears in logs/errors/repr."""
    sentinel_secret = "SUPER_CONFIDENTIAL_RECEIPT_SECRET_778899"
    os.environ["AKAAL_GATEWAY_RECEIPT_SECRET"] = sentinel_secret

    resp = GatewayResponse.create_success(
        operation_id="op-succ-004",
        operation_type="TEST_OPERATION",
        migration_id="mig-001",
        run_id="run-001",
        payload={},
    )
    repr_str = repr(resp)
    assert sentinel_secret not in repr_str
    if resp.execution_receipt:
        assert sentinel_secret not in str(resp.execution_receipt)


def test_engine_gateway_execute_missing_secret_fails_closed():
    """EngineGateway.execute with missing secret fails closed cleanly without unhandled exception."""
    os.environ.pop("AKAAL_GATEWAY_RECEIPT_SECRET", None)

    gateway = EngineGateway()
    ctx = GatewayRequestContext(
        migration_id="mig-no-sec-001",
        run_id="run-no-sec-001",
        job_id="job-no-sec-001",
        fencing_epoch=1,
    )
    req = GatewayRequest(
        operation=SemanticOperation.GET_HEALTH_DIAGNOSTICS,
        context=ctx,
        payload={},
    )
    resp = gateway.execute(req)
    assert resp.success is False
    assert resp.failure_category in (
        GatewayFailureCategory.INTERNAL_ENGINE_FAILURE.value,
        GatewayFailureCategory.PERMISSION_FAILURE.value,
    )
    assert "receipt secret is not provisioned" in resp.error_message
    assert resp.execution_receipt is None
