"""
AKAAL CDC Engine Failure Taxonomy & Exception Hierarchy.
=========================================================
Classifies CDC errors into RETRYABLE, PAUSABLE, BLOCKING, TERMINAL, and DATA_INTEGRITY_RISK categories.
"""

from enum import Enum
from typing import Dict, Any, Optional
import datetime


class CDCFailureCategory(str, Enum):
    """Failure categorization for CDC runtime errors."""
    RETRYABLE = "RETRYABLE"
    PAUSABLE = "PAUSABLE"
    BLOCKING = "BLOCKING"
    TERMINAL = "TERMINAL"
    DATA_INTEGRITY_RISK = "DATA_INTEGRITY_RISK"


class CDCFailureType(str, Enum):
    """Specific CDC failure classification types."""
    CDC_PREREQUISITE_MISSING = "CDC_PREREQUISITE_MISSING"
    SOURCE_DISCONNECT = "SOURCE_DISCONNECT"
    SOURCE_POSITION_INVALID = "SOURCE_POSITION_INVALID"
    SOURCE_LOG_UNAVAILABLE = "SOURCE_LOG_UNAVAILABLE"
    DECODER_FAILURE = "DECODER_FAILURE"
    MALFORMED_EVENT = "MALFORMED_EVENT"
    TRANSACTION_CORRUPTION = "TRANSACTION_CORRUPTION"
    DURABLE_BUFFER_FAILURE = "DURABLE_BUFFER_FAILURE"
    TARGET_DISCONNECT = "TARGET_DISCONNECT"
    TARGET_TRANSACTION_FAILURE = "TARGET_TRANSACTION_FAILURE"
    CONSTRAINT_FAILURE = "CONSTRAINT_FAILURE"
    CHECKPOINT_CORRUPTION = "CHECKPOINT_CORRUPTION"
    WORKER_CRASH = "WORKER_CRASH"
    SCHEMA_DRIFT_DURING_CDC = "SCHEMA_DRIFT_DURING_CDC"
    CONSISTENCY_BOUNDARY_VIOLATION = "CONSISTENCY_BOUNDARY_VIOLATION"


class CDCFailure:
    """Structured CDC failure record."""

    def __init__(
        self,
        failure_type: CDCFailureType,
        category: CDCFailureCategory,
        message: str,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.failure_type = failure_type
        self.category = category
        self.message = message
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.cdc_session_id = cdc_session_id
        self.details = details or {}
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "category": self.category.value,
            "message": self.message,
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "cdc_session_id": self.cdc_session_id,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class CDCExecutionError(Exception):
    """Base exception for CDC runtime execution failures."""

    def __init__(self, failure: CDCFailure) -> None:
        super().__init__(f"[{failure.category.value}] {failure.failure_type.value}: {failure.message}")
        self.failure = failure
