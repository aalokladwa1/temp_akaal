"""
AKAAL Platform 5 — Domain Exceptions Hierarchy

Defines structured exception models across all Platform 5 subsystems.
Every exception carries context, root cause, recovery recommendations, and correlation IDs.
"""

from typing import Any, Dict, Optional


class SchemaEvolutionError(Exception):
    """Base exception for all Platform 5 Schema Evolution errors."""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_recommendation: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id or "CORR-UNSPECIFIED"
        self.context = context or {}
        self.recovery_recommendation = recovery_recommendation or "Review error log and diagnostic details."
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "context": self.context,
            "recovery_recommendation": self.recovery_recommendation,
            "cause": str(self.cause) if self.cause else None,
        }


class TransactionError(SchemaEvolutionError):
    """Raised when a schema transaction fails during lifecycle transitions or commit/rollback."""
    pass


class ValidationError(SchemaEvolutionError):
    """Raised when one or more stages of the validation pipeline fail."""
    pass


class ReplayError(SchemaEvolutionError):
    """Raised when DDL operation journal replay encounters errors or checksum mismatches."""
    pass


class RecoveryError(SchemaEvolutionError):
    """Raised when automatic compensation or failure recovery procedures fail."""
    pass


class MetadataError(SchemaEvolutionError):
    """Raised when metadata snapshots, cache operations, or refresh routines fail."""
    pass


class ConcurrencyError(SchemaEvolutionError):
    """Raised when lock contention, deadlock, or optimistic concurrency version conflicts occur."""
    pass


class JournalIntegrityError(ReplayError):
    """Raised when an immutable operation journal record hash chain is tampered with or corrupted."""
    pass


class VersionConflictError(ConcurrencyError):
    """Raised when OCC fails due to version sequence divergence."""
    pass


class IncompatibleSchemaError(ValidationError):
    """Raised when a schema change violates backward compatibility constraints."""
    pass


class ExecutionError(SchemaEvolutionError):
    """Raised when a live schema DDL statement execution fails."""
    pass
