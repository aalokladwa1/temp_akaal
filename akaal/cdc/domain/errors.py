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
    TRANSACTION_CORRUPTION = "TRANSACTION_CORRUPTION"
    DURABLE_BUFFER_FAILURE = "DURABLE_BUFFER_FAILURE"
    BUFFER_CORRUPTION = "BUFFER_CORRUPTION"
    STALE_WORKER = "STALE_WORKER"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    UNSAFE_DELETE = "UNSAFE_DELETE"
    UNSAFE_UPDATE = "UNSAFE_UPDATE"
    TARGET_APPLY_FAILURE = "TARGET_APPLY_FAILURE"
    TARGET_COMMIT_FAILURE = "TARGET_COMMIT_FAILURE"
    CHECKPOINT_FAILURE = "CHECKPOINT_FAILURE"
    MALFORMED_EVENT = "MALFORMED_EVENT"
    TARGET_DISCONNECT = "TARGET_DISCONNECT"
    TARGET_TRANSACTION_FAILURE = "TARGET_TRANSACTION_FAILURE"
    CONSTRAINT_FAILURE = "CONSTRAINT_FAILURE"
    CHECKPOINT_CORRUPTION = "CHECKPOINT_CORRUPTION"
    WORKER_CRASH = "WORKER_CRASH"
    SCHEMA_DRIFT_DURING_CDC = "SCHEMA_DRIFT_DURING_CDC"
    SCHEMA_BARRIER_ACTIVE = "SCHEMA_BARRIER_ACTIVE"
    CONSISTENCY_BOUNDARY_VIOLATION = "CONSISTENCY_BOUNDARY_VIOLATION"
    PARTITION_ROUTING_FAILURE = "PARTITION_ROUTING_FAILURE"
    PARTITION_OWNERSHIP_CONFLICT = "PARTITION_OWNERSHIP_CONFLICT"
    STALE_PARTITION_WORKER = "STALE_PARTITION_WORKER"
    CROSS_PARTITION_BARRIER_FAILURE = "CROSS_PARTITION_BARRIER_FAILURE"
    PARALLEL_APPLY_FAILURE = "PARALLEL_APPLY_FAILURE"
    REBALANCE_FAILURE = "REBALANCE_FAILURE"
    CHECKPOINT_FRONTIER_BLOCKED = "CHECKPOINT_FRONTIER_BLOCKED"
    CAUSALITY_CYCLE_DETECTED = "CAUSALITY_CYCLE_DETECTED"
    MISSING_PREDECESSOR = "MISSING_PREDECESSOR"
    FAILED_PREDECESSOR = "FAILED_PREDECESSOR"
    CAUSAL_STATE_CORRUPTION = "CAUSAL_STATE_CORRUPTION"
    DEPENDENCY_IDENTITY_MISMATCH = "DEPENDENCY_IDENTITY_MISMATCH"
    STALE_ORDERING_WORKER = "STALE_ORDERING_WORKER"
    UNRESOLVED_CAUSAL_DEPENDENCY = "UNRESOLVED_CAUSAL_DEPENDENCY"
    INVALID_DEPENDENCY_EDGE = "INVALID_DEPENDENCY_EDGE"
    TOPOLOGY_IDENTITY_MISMATCH = "TOPOLOGY_IDENTITY_MISMATCH"
    TOPOLOGY_STATE_CORRUPTION = "TOPOLOGY_STATE_CORRUPTION"
    REPLICATION_LOOP_DETECTED = "REPLICATION_LOOP_DETECTED"
    INVALID_ORIGIN_PROVENANCE = "INVALID_ORIGIN_PROVENANCE"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    CONFLICT_STATE_CORRUPTION = "CONFLICT_STATE_CORRUPTION"
    CONFLICT_RESOLUTION_REJECTED = "CONFLICT_RESOLUTION_REJECTED"
    QUARANTINE_FAILURE = "QUARANTINE_FAILURE"
    STALE_CONFLICT_RESOLVER = "STALE_CONFLICT_RESOLVER"
    UNSAFE_LATEST_VERSION_COMPARISON = "UNSAFE_LATEST_VERSION_COMPARISON"


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
