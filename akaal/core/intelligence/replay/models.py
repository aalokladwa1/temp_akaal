"""
Akaal — Replay Subsystem Models
===============================
Defines the state Enums, immutable event representations, timeline tracking,
checkpoint records, and statistics models for the Replay subsystem.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple


class ReplayState(str, Enum):
    INITIALIZED = "INITIALIZED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RESUMED = "RESUMED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


VALID_TRANSITIONS: Dict[ReplayState, Set[ReplayState]] = {
    ReplayState.INITIALIZED: {ReplayState.VALIDATING, ReplayState.CANCELLED},
    ReplayState.VALIDATING: {ReplayState.READY, ReplayState.FAILED, ReplayState.CANCELLED},
    ReplayState.READY: {ReplayState.ACTIVE, ReplayState.CANCELLED},
    ReplayState.ACTIVE: {ReplayState.SUSPENDED, ReplayState.COMPLETED, ReplayState.FAILED, ReplayState.CANCELLED},
    ReplayState.SUSPENDED: {ReplayState.RESUMED, ReplayState.EXPIRED, ReplayState.CANCELLED},
    ReplayState.RESUMED: {ReplayState.VALIDATING, ReplayState.FAILED, ReplayState.CANCELLED},
    ReplayState.COMPLETED: set(),
    ReplayState.FAILED: set(),
    ReplayState.CANCELLED: set(),
    ReplayState.EXPIRED: set(),
}


@dataclass(frozen=True)
class CDCEventModel:
    """Immutable CDC transaction event description."""
    event_id: str
    commit_sequence: int  # Unified commit LSN/SCN/Binlog offset
    timestamp: datetime
    operation: str        # INSERT, UPDATE, DELETE
    table_key: str
    payload_hash: str
    transaction_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayCheckpoint:
    """Immutable session watermark state capture."""
    checkpoint_id: str
    session_id: str
    commit_sequence: int
    timestamp: datetime
    payload_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SequenceGap:
    """Represents a missing span in sequential commit logs."""
    start_sequence: int
    end_sequence: int
    missing_count: int


@dataclass(frozen=True)
class OutOfOrderEvent:
    """Identifies an event violating serial log sequencing."""
    expected_sequence: int
    actual_sequence: int
    event: CDCEventModel


@dataclass(frozen=True)
class TimelineStatistics:
    """Trace metrics aggregated across a CDC replay event sequence."""
    total_events: int
    insert_count: int
    update_count: int
    delete_count: int
    sequence_gaps_count: int
    out_of_order_count: int
    min_sequence: int
    max_sequence: int
    duration_seconds: float


@dataclass(frozen=True)
class SessionStatistics:
    """Execution state telemetry for the replay session."""
    total_transitions: int
    active_duration_seconds: float
    error_count: int
    last_checkpoint_sequence: int
    checkpoint_count: int


@dataclass(frozen=True)
class ReplayTimeline:
    """Ordered event sequence representing replicated transaction statements."""
    timeline_id: str
    events: Tuple[CDCEventModel, ...]
    statistics: TimelineStatistics


@dataclass(frozen=True)
class ReplaySession:
    """State tracking container representing an active replication validator run."""
    session_id: str
    state: ReplayState
    timeline: ReplayTimeline
    checkpoints: Tuple[ReplayCheckpoint, ...]
    statistics: SessionStatistics
    created_at: datetime
    updated_at: datetime
