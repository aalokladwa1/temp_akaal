"""
Hierarchical Checkpoint and Position Models for Authority #5 — Durability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


from akaalEngine.durability.models.errors import InvalidResumePositionError


class RowPositionType(str, Enum):
    PRIMARY_KEY = "PRIMARY_KEY"
    COMPOSITE_PRIMARY_KEY = "COMPOSITE_PRIMARY_KEY"
    UNIQUE_KEY = "UNIQUE_KEY"
    PROVIDER_ROW_IDENTITY = "PROVIDER_ROW_IDENTITY"  # e.g. Oracle ROWID, Postgres ctid
    ORDERED_KEYSET = "ORDERED_KEYSET"
    SOURCE_SNAPSHOT_POSITION = "SOURCE_SNAPSHOT_POSITION"
    BYTE_OFFSET = "BYTE_OFFSET"
    RECORD_OFFSET = "RECORD_OFFSET"
    OBJECT_CONTINUATION = "OBJECT_CONTINUATION"
    PROVIDER_TOKEN = "PROVIDER_TOKEN"
    UNSAFE_UNAVAILABLE = "UNSAFE_UNAVAILABLE"


@dataclass(frozen=True)
class RowPosition:
    """Generalized resumable row position model."""
    position_type: RowPositionType
    value: Dict[str, Any]
    is_stable_resume_supported: bool = True
    column_names: Tuple[str, ...] = ()
    token: Optional[str] = None

    def __post_init__(self) -> None:
        if self.position_type == RowPositionType.UNSAFE_UNAVAILABLE and self.is_stable_resume_supported:
            raise InvalidResumePositionError("RowPosition with UNSAFE_UNAVAILABLE position_type cannot claim is_stable_resume_supported=True.")

    @classmethod
    def create_pk(cls, columns: Tuple[str, ...], values: Dict[str, Any]) -> "RowPosition":
        pos_type = RowPositionType.PRIMARY_KEY if len(columns) == 1 else RowPositionType.COMPOSITE_PRIMARY_KEY
        return cls(position_type=pos_type, value=values, is_stable_resume_supported=True, column_names=columns)

    @classmethod
    def create_provider_token(cls, token: str) -> "RowPosition":
        return cls(position_type=RowPositionType.PROVIDER_TOKEN, value={"token": token}, is_stable_resume_supported=True, token=token)

    @classmethod
    def create_unsafe_unavailable(cls, reason: str = "Unordered table lacking primary/unique key") -> "RowPosition":
        return cls(position_type=RowPositionType.UNSAFE_UNAVAILABLE, value={"reason": reason}, is_stable_resume_supported=False)


@dataclass(frozen=True)
class TableCheckpoint:
    """Per-table checkpoint progress representation."""
    table_name: str
    schema_name: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    rows_processed: int = 0
    bytes_processed: int = 0
    last_position: Optional[RowPosition] = None
    partition_id: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class MigrationCheckpoint:
    """Top-level migration run checkpoint snapshot."""
    migration_id: str
    job_id: str
    fencing_epoch: int
    status: str  # PENDING, IN_PROGRESS, PAUSED, COMPLETED, FAILED
    table_checkpoints: Dict[str, TableCheckpoint] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: Optional[str] = None
    checksum: Optional[str] = None


# DUR-017: Change Capture CDC Position Seam
@dataclass(frozen=True)
class CDCOffsetDurabilitySeam:
    """Provider-neutral CDC offset storage DTO."""
    cdc_session_id: str
    provider_name: str  # postgresql, oracle, mysql, mongodb, kafka
    position_token: str
    fencing_epoch: int
    captured_at: str
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


# DUR-018: Transport Resumable Progress Seam
@dataclass(frozen=True)
class TransportCheckpointSeam:
    """Resumable Transport chunk progress storage DTO."""
    transfer_id: str
    chunk_id: str
    bytes_transferred: int
    records_transferred: int
    is_completed: bool
    staged_file_ref: Optional[str] = None
    updated_at: Optional[str] = None


# DUR-020: Validation Checkpoint Seam
@dataclass(frozen=True)
class ValidationCheckpointSeam:
    """Resumable Validation progress storage DTO."""
    validation_run_id: str
    table_name: str
    verified_rows: int
    mismatched_rows: int
    last_verified_key: Optional[RowPosition] = None
    status: str = "IN_PROGRESS"
