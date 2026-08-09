"""
AKAAL Platform — Centralized Error Taxonomy & Error Classification Framework
==========================================================================
Provides standardized classification of database, network, resource, and execution
errors across all migration lifecycle stages.
"""

from enum import Enum
from typing import Dict, Any, Optional
import re


class ErrorCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    RESOURCE_CAPACITY = "RESOURCE_CAPACITY"
    CONFIGURATION = "CONFIGURATION"
    PERMISSION = "PERMISSION"
    DATA = "DATA"
    UNSUPPORTED = "UNSUPPORTED"
    INTERNAL = "INTERNAL"


class ErrorClassification:
    """Encapsulates a categorized error diagnostic with remediation guidance."""

    def __init__(
        self,
        error_code: str,
        category: ErrorCategory,
        retryable: bool,
        stage: str,
        engine: str,
        message: str,
        remediation: str,
        original_error_type: str,
        sqlstate: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.error_code = error_code
        self.category = category
        self.retryable = retryable
        self.stage = stage
        self.engine = engine
        self.message = message
        self.remediation = remediation
        self.original_error_type = original_error_type
        self.sqlstate = sqlstate
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "category": self.category.value if isinstance(self.category, ErrorCategory) else str(self.category),
            "retryable": self.retryable,
            "stage": self.stage,
            "engine": self.engine,
            "message": self.message,
            "remediation": self.remediation,
            "original_error_type": self.original_error_type,
            "sqlstate": self.sqlstate,
            "details": self.details,
        }


class ErrorTaxonomy:
    """Centralized diagnostic engine that maps database exceptions & SQLSTATE codes to standardized classification."""

    @classmethod
    def classify(
        cls,
        exc: Exception,
        stage: str = "SCHEMA_EXECUTION",
        engine: str = "POSTGRESQL",
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorClassification:
        exc_type = type(exc).__name__
        msg = str(exc)
        sqlstate = getattr(exc, "pgcode", getattr(exc, "sqlstate", None))

        # 1. PostgreSQL Lock & Shared-Memory Capacity Exhaustion
        if (
            sqlstate in ("53200", "53000", "53100") or
            "out of shared memory" in msg.lower() or
            "max_locks_per_transaction" in msg.lower() or
            "lock table is full" in msg.lower()
        ):
            return ErrorClassification(
                error_code="POSTGRES_LOCK_CAPACITY_EXHAUSTED",
                category=ErrorCategory.RESOURCE_CAPACITY,
                retryable=False,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="PostgreSQL lock-table shared memory exhausted. AKAAL bounded DDL execution strategy will reduce transaction group lock footprint. If target capacity remains insufficient, PostgreSQL max_locks_per_transaction configuration may require adjustment.",
                original_error_type=exc_type,
                sqlstate=sqlstate or "53200",
                details=details
            )

        # 2. Authentication / Permission Failures
        if (
            sqlstate in ("28000", "28P01", "42501") or
            "password authentication failed" in msg.lower() or
            "permission denied" in msg.lower() or
            "access denied" in msg.lower() or
            "ORA-01017" in msg
        ):
            return ErrorClassification(
                error_code="AUTHENTICATION_OR_PERMISSION_DENIED",
                category=ErrorCategory.PERMISSION,
                retryable=False,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Verify database user credentials, role permissions, and object-level schema privileges.",
                original_error_type=exc_type,
                sqlstate=sqlstate or "28000",
                details=details
            )

        # 3. Connection Authority Mismatch
        if "authority_mismatch" in msg.lower() or "source_connection_authority_mismatch" in msg.lower():
            return ErrorClassification(
                error_code="SOURCE_CONNECTION_AUTHORITY_MISMATCH",
                category=ErrorCategory.CONFIGURATION,
                retryable=False,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Source connection configuration used at runtime differs from user-tested/approved source connection authority.",
                original_error_type=exc_type,
                sqlstate=sqlstate,
                details=details
            )

        if "target_connection_authority_mismatch" in msg.lower() or "authority mismatch" in msg.lower():
            return ErrorClassification(
                error_code="TARGET_CONNECTION_AUTHORITY_MISMATCH",
                category=ErrorCategory.CONFIGURATION,
                retryable=False,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Target connection configuration used at runtime differs from user-tested/approved target connection authority.",
                original_error_type=exc_type,
                sqlstate=sqlstate,
                details=details
            )

        # 4. Connection Refused / Pre-Start Connectivity Failures
        if "source_connection_refused" in msg.lower() or ("source" in msg.lower() and ("connection refused" in msg.lower() or "could not connect" in msg.lower())):
            return ErrorClassification(
                error_code="SOURCE_CONNECTION_REFUSED",
                category=ErrorCategory.TRANSIENT,
                retryable=True,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Could not reach source database host/port. Verify network connectivity, firewall, and database service listener.",
                original_error_type=exc_type,
                sqlstate=sqlstate or "08001",
                details=details
            )

        if "target_connection_refused" in msg.lower() or "connection refused" in msg.lower() or "could not connect" in msg.lower():
            return ErrorClassification(
                error_code="TARGET_CONNECTION_REFUSED",
                category=ErrorCategory.TRANSIENT,
                retryable=True,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Could not reach target database host/port. Verify PostgreSQL service status, network firewall, and connection settings.",
                original_error_type=exc_type,
                sqlstate=sqlstate or "08001",
                details=details
            )

        # 5. Connection & Transient Network Resets
        if (
            sqlstate in ("08000", "08003", "08006", "08001", "08004", "57P01") or
            "connection reset" in msg.lower() or
            "timeout" in msg.lower() or
            "closed unexpectedly" in msg.lower()
        ):
            return ErrorClassification(
                error_code="DATABASE_CONNECTION_TRANSIENT",
                category=ErrorCategory.TRANSIENT,
                retryable=True,
                stage=stage,
                engine=engine,
                message=msg,
                remediation="Transient network or database connection interruption detected. Automated retry will attempt reconnect.",
                original_error_type=exc_type,
                sqlstate=sqlstate or "08006",
                details=details
            )


        # 5. Generic Internal / Fallback Error
        return ErrorClassification(
            error_code="UNHANDLED_ENGINE_ERROR",
            category=ErrorCategory.INTERNAL,
            retryable=False,
            stage=stage,
            engine=engine,
            message=msg,
            remediation="Inspect error log trace for detailed root cause diagnostics.",
            original_error_type=exc_type,
            sqlstate=sqlstate,
            details=details
        )
