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
