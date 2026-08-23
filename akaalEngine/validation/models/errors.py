"""
akaalEngine.validation.models.errors
===================================
Typed Exception Hierarchy for Authority #11 Validation / Reconciliation / Data Correctness.
"""

from typing import Any, Dict, Optional


class ValidationError(Exception):
    """Base exception for Authority #11 Validation."""
    def __init__(self, message: str, error_code: str = "VAL_ERROR", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class ValidationPlanError(ValidationError):
    """Raised when a ValidationPlan is invalid or unexecutable."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="VAL_PLAN_INVALID")


class SchemaValidationError(ValidationError):
    """Raised when target schema structure or column mappings fail validation."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="VAL_SCHEMA_MISMATCH", details=details)


class CardinalityValidationError(ValidationError):
    """Raised when row counts between source and target disagree beyond approved filtering."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="VAL_CARDINALITY_MISMATCH", details=details)


class FingerprintError(ValidationError):
    """Raised when canonical fingerprint computation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="VAL_FINGERPRINT_ERROR")


class ReconciliationMismatchError(ValidationError):
    """Raised when exact row reconciliation detects corrupt, missing, or extra records."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="VAL_RECONCILIATION_MISMATCH", details=details)


class ValidationGateError(ValidationError):
    """Raised when VALIDATION_GATE fails closed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="VALIDATION_GATE_FAILED", details=details)


class ValidationTimeoutError(ValidationError):
    """Raised when validation operation exceeds configured timeout."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="VAL_TIMEOUT")


class ValidationFencingError(ValidationError):
    """Raised when Authority #5 fencing token validation fails during validation."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="VAL_FENCING_ERROR")


class ValidationCancelledError(ValidationError):
    """Raised when validation execution is cancelled via Authority #6 CancellationToken."""
    def __init__(self, reason: str = "Validation cancelled") -> None:
        super().__init__(f"Validation cancelled: {reason}", error_code="VAL_CANCELLED")
