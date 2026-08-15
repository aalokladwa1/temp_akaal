"""
AKAAL CDC Engine Event & Transaction Domain Models.
===================================================
Identity-bound CDC events, transactional boundaries, and secrets-redacted diagnostics with recursive sanitization.
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCEventIdentity":
        return cls(
            migration_id=data["migration_id"],
            job_id=data["job_id"],
            run_id=data["run_id"],
            cdc_session_id=data["cdc_session_id"],
            event_id=data.get("event_id"),
            sequence_number=data.get("sequence_number", 1),
        )


class CDCEvent:
    """
    Canonical CDC Change Event domain object.
    Preserves identity, transactional context, engine-specific source position, before/after states,
    and provides data-safe diagnostic sanitization.
    """

    SECRET_KEYWORDS = {"password", "passwd", "secret", "token", "api_key", "authorization", "private_key", "connection_string", "auth_token"}

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
        schema_version_id: Optional[str] = None,
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
        self.schema_version_id = schema_version_id

    @classmethod
    def _sanitize_dict_recursive(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in cls.SECRET_KEYWORDS):
                    sanitized[k] = "[REDACTED_SECRET]"
                else:
                    sanitized[k] = cls._sanitize_dict_recursive(v)
            return sanitized
        elif isinstance(data, list):
            return [cls._sanitize_dict_recursive(item) for item in data]
        return data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "source_engine": self.source_engine,
            "source_database": self.source_database,
            "source_schema": self.source_schema,
            "source_table": self.source_table,
            "operation": self.operation.value,
            "position": self.position.to_dict(),
            "before_image": self._sanitize_dict_recursive(self.before_image),
            "after_image": self._sanitize_dict_recursive(self.after_image),
            "boundary": self.boundary.value,
            "tx_id": self.tx_id,
            "commit_timestamp": self.commit_timestamp,
            "captured_timestamp": self.captured_timestamp,
            "schema_version_id": self.schema_version_id,
        }

    def to_data_safe_dict(self) -> Dict[str, Any]:
        """Returns a diagnostic summary that redacts actual customer row contents and nested secrets."""
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
            "before_keys": list(self.before_image.keys()) if isinstance(self.before_image, dict) else [],
            "after_keys": list(self.after_image.keys()) if isinstance(self.after_image, dict) else [],
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
        if event.identity.migration_id != self.identity.migration_id or event.identity.run_id != self.identity.run_id:
            raise ValueError(f"Cross-migration/run event substitution rejected for transaction '{self.tx_id}'.")
        self.events.append(event)

    def mark_commit(self) -> None:
        if self.is_aborted:
            raise ValueError(f"Cannot commit aborted transaction '{self.tx_id}'.")
        self.is_committed = True

    def mark_abort(self) -> None:
        if self.is_committed:
            raise ValueError(f"Cannot abort committed transaction '{self.tx_id}'.")
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
            "events": [e.to_dict() for e in self.events],
        }


def parse_cdc_event(data: Dict[str, Any]) -> CDCEvent:
    ident_dict = data["identity"]
    identity = CDCEventIdentity(
        migration_id=ident_dict["migration_id"],
        job_id=ident_dict["job_id"],
        run_id=ident_dict["run_id"],
        cdc_session_id=ident_dict["cdc_session_id"],
        event_id=ident_dict.get("event_id"),
        sequence_number=ident_dict.get("sequence_number", 1),
    )
    pos = parse_source_position(data["position"])
    op = CDCOperationType(data["operation"])
    boundary = CDCTransactionBoundary(data.get("boundary", "SINGLE_EVENT"))

    return CDCEvent(
        identity=identity,
        source_engine=data["source_engine"],
        source_database=data["source_database"],
        source_schema=data["source_schema"],
        source_table=data["source_table"],
        operation=op,
        position=pos,
        before_image=data.get("before_image"),
        after_image=data.get("after_image"),
        boundary=boundary,
        tx_id=data.get("tx_id"),
        commit_timestamp=data.get("commit_timestamp"),
        captured_timestamp=data.get("captured_timestamp"),
    )


def parse_cdc_transaction(data: Dict[str, Any]) -> CDCTransaction:
    ident_dict = data["identity"]
    identity = CDCEventIdentity(
        migration_id=ident_dict["migration_id"],
        job_id=ident_dict["job_id"],
        run_id=ident_dict["run_id"],
        cdc_session_id=ident_dict["cdc_session_id"],
        event_id=ident_dict.get("event_id"),
        sequence_number=ident_dict.get("sequence_number", 1),
    )
    pos = parse_source_position(data["commit_position"])
    events = [parse_cdc_event(e) for e in data.get("events", [])]

    tx = CDCTransaction(
        tx_id=data["tx_id"],
        identity=identity,
        commit_position=pos,
        events=events,
        commit_timestamp=data.get("commit_timestamp"),
    )
    if data.get("is_committed", True):
        tx.is_committed = True
    if data.get("is_aborted", False):
        tx.is_aborted = True
    return tx
