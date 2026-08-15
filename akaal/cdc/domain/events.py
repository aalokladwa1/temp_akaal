"""
AKAAL CDC Engine Event & Transaction Domain Models.
===================================================
Identity-bound CDC events, transactional boundaries, and secrets-redacted diagnostic representations.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
import datetime
import uuid

from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position


class CDCOperationType(str, Enum):
    """Supported CDC operation categories."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"


class CDCTransactionBoundary(str, Enum):
    """Transactional boundary semantics for source change streams."""
    BEGIN = "BEGIN"
    EVENT = "EVENT"
    COMMIT = "COMMIT"
    ABORT = "ABORT"
    SINGLE_EVENT = "SINGLE_EVENT"


class CDCEventIdentity:
    """Strongly-typed identity structure binding every CDC event to migration, job, run, and CDC session."""

    def __init__(
        self,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        event_id: Optional[str] = None,
        sequence_number: int = 1,
    ) -> None:
        if not migration_id or not job_id or not run_id or not cdc_session_id:
            raise ValueError("All identity bindings (migration_id, job_id, run_id, cdc_session_id) must be non-empty.")
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.cdc_session_id = cdc_session_id
        self.event_id = event_id or f"ev-cdc-{uuid.uuid4().hex[:12]}"
        self.sequence_number = sequence_number

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "cdc_session_id": self.cdc_session_id,
            "event_id": self.event_id,
            "sequence_number": self.sequence_number,
        }


class CDCEvent:
    """
    Canonical CDC Change Event domain object.
    Preserves identity, transactional context, engine-specific source position, before/after states,
    and provides data-safe diagnostic sanitization.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        source_engine: str,
        source_database: str,
        source_schema: str,
        source_table: str,
        operation: CDCOperationType,
        position: CDCSourcePosition,
        before_image: Optional[Dict[str, Any]] = None,
        after_image: Optional[Dict[str, Any]] = None,
        boundary: CDCTransactionBoundary = CDCTransactionBoundary.SINGLE_EVENT,
        tx_id: Optional[str] = None,
        commit_timestamp: Optional[str] = None,
        captured_timestamp: Optional[str] = None,
    ) -> None:
        self.identity = identity
        self.source_engine = source_engine.upper()
        self.source_database = source_database
        self.source_schema = source_schema
        self.source_table = source_table
        self.operation = operation
        self.position = position
        self.before_image = before_image
        self.after_image = after_image
        self.boundary = boundary
        self.tx_id = tx_id
        self.commit_timestamp = commit_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.captured_timestamp = captured_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "source_engine": self.source_engine,
            "source_database": self.source_database,
            "source_schema": self.source_schema,
            "source_table": self.source_table,
            "operation": self.operation.value,
            "position": self.position.to_dict(),
            "before_image": self.before_image,
            "after_image": self.after_image,
            "boundary": self.boundary.value,
            "tx_id": self.tx_id,
            "commit_timestamp": self.commit_timestamp,
            "captured_timestamp": self.captured_timestamp,
        }

    def to_data_safe_dict(self) -> Dict[str, Any]:
        """Returns a diagnostic summary that redacts actual customer row contents."""
        return {
            "identity": self.identity.to_dict(),
            "source_engine": self.source_engine,
            "table_fqn": f"{self.source_schema}.{self.source_table}",
            "operation": self.operation.value,
            "position": self.position.to_string(),
            "boundary": self.boundary.value,
            "tx_id": self.tx_id,
            "has_before_image": self.before_image is not None,
            "has_after_image": self.after_image is not None,
            "before_keys": list(self.before_image.keys()) if self.before_image else [],
            "after_keys": list(self.after_image.keys()) if self.after_image else [],
            "captured_timestamp": self.captured_timestamp,
        }


class CDCTransaction:
    """Ordered grouping of CDC Events comprising a single source database transaction."""

    def __init__(
        self,
        tx_id: str,
        identity: CDCEventIdentity,
        commit_position: CDCSourcePosition,
        events: Optional[List[CDCEvent]] = None,
        commit_timestamp: Optional[str] = None,
    ) -> None:
        self.tx_id = tx_id
        self.identity = identity
        self.commit_position = commit_position
        self.events: List[CDCEvent] = events or []
        self.commit_timestamp = commit_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.is_committed = False
        self.is_aborted = False

    def add_event(self, event: CDCEvent) -> None:
        if self.is_committed or self.is_aborted:
            raise ValueError(f"Cannot add event to finalized transaction '{self.tx_id}'.")
        self.events.append(event)

    def mark_commit(self) -> None:
        self.is_committed = True

    def mark_abort(self) -> None:
        self.is_aborted = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "identity": self.identity.to_dict(),
            "commit_position": self.commit_position.to_dict(),
            "event_count": len(self.events),
            "is_committed": self.is_committed,
            "is_aborted": self.is_aborted,
            "commit_timestamp": self.commit_timestamp,
        }
