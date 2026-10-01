"""
akaalEngine.cdc.models.event
============================
Canonical ChangeEvent and TransactionContext dataclasses.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


class ChangeOperation(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    DDL = "DDL"
    HEARTBEAT = "HEARTBEAT"


class DeletionType(str, Enum):
    EXPLICIT_DELETE = "EXPLICIT_DELETE"
    TOMBSTONE = "TOMBSTONE"
    TTL_EXPIRY = "TTL_EXPIRY"
    DELETE_UNAVAILABLE = "DELETE_UNAVAILABLE"


@dataclass(frozen=True)
class TransactionContext:
    tx_id: str
    commit_timestamp_iso: str
    sequence_number: int
    total_events_in_tx: Optional[int] = None


@dataclass
class ChangeEvent:
    event_id: str
    source_system: str
    source_identity: str
    logical_object: str
    operation: ChangeOperation
    source_position: str
    commit_position: str
    commit_timestamp: float
    capture_timestamp: float
    schema_version: str
    key_columns: Tuple[str, ...]
    key_values: Mapping[str, Any]
    before_image: Optional[Mapping[str, Any]] = None
    after_image: Optional[Mapping[str, Any]] = None
    changed_columns: Optional[Tuple[str, ...]] = None
    tx_context: Optional[TransactionContext] = None
    deletion_type: DeletionType = DeletionType.EXPLICIT_DELETE
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tx_dict = None
        if self.tx_context is not None:
            tx_dict = {
                "tx_id": self.tx_context.tx_id,
                "commit_timestamp_iso": self.tx_context.commit_timestamp_iso,
                "sequence_number": self.tx_context.sequence_number,
                "total_events_in_tx": self.tx_context.total_events_in_tx,
            }
        return {
            "event_id": self.event_id,
            "source_system": self.source_system,
            "source_identity": self.source_identity,
            "logical_object": self.logical_object,
            "operation": self.operation.value if isinstance(self.operation, ChangeOperation) else str(self.operation),
            "source_position": self.source_position,
            "commit_position": self.commit_position,
            "commit_timestamp": self.commit_timestamp,
            "capture_timestamp": self.capture_timestamp,
            "schema_version": self.schema_version,
            "key_columns": list(self.key_columns),
            "key_values": dict(self.key_values) if self.key_values else {},
            "before_image": dict(self.before_image) if self.before_image is not None else None,
            "after_image": dict(self.after_image) if self.after_image is not None else None,
            "changed_columns": list(self.changed_columns) if self.changed_columns is not None else None,
            "tx_context": tx_dict,
            "deletion_type": self.deletion_type.value if isinstance(self.deletion_type, DeletionType) else str(self.deletion_type),
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ChangeEvent:
        tx_ctx = None
        if d.get("tx_context"):
            tc = d["tx_context"]
            tx_ctx = TransactionContext(
                tx_id=tc["tx_id"],
                commit_timestamp_iso=tc["commit_timestamp_iso"],
                sequence_number=tc["sequence_number"],
                total_events_in_tx=tc.get("total_events_in_tx"),
            )
        del_type = DeletionType(d.get("deletion_type", DeletionType.EXPLICIT_DELETE.value))
        op = ChangeOperation(d["operation"])
        return cls(
            event_id=d["event_id"],
            source_system=d["source_system"],
            source_identity=d["source_identity"],
            logical_object=d["logical_object"],
            operation=op,
            source_position=d["source_position"],
            commit_position=d["commit_position"],
            commit_timestamp=float(d["commit_timestamp"]),
            capture_timestamp=float(d["capture_timestamp"]),
            schema_version=d["schema_version"],
            key_columns=tuple(d.get("key_columns", ())),
            key_values=d.get("key_values", {}),
            before_image=d.get("before_image"),
            after_image=d.get("after_image"),
            changed_columns=tuple(d["changed_columns"]) if d.get("changed_columns") is not None else None,
            tx_context=tx_ctx,
            deletion_type=del_type,
            metadata=d.get("metadata", {}),
        )
