from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

class CDCOperationType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"

class CDCSessionState(str, Enum):
    INITIALIZING = "INITIALIZING"
    CATCHING_UP = "CATCHING_UP"
    STREAMING = "STREAMING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

class ConflictResolutionPolicy(str, Enum):
    SOURCE_WINS = "SOURCE_WINS"
    TARGET_WINS = "TARGET_WINS"
    SKIP = "SKIP"
    ABORT = "ABORT"

@dataclass(frozen=True)
class SynchronizationConfiguration:
    session_id: str
    source_dialect: str
    target_dialect: str
    conflict_policy: ConflictResolutionPolicy
    batch_size: int
    max_queue_depth: int
    retry_limit: int
    retry_backoff_factor: float
    heartbeat_interval_seconds: float

    def validate(self) -> None:
        if self.batch_size < 1 or self.batch_size > 10000:
            raise ValueError("Batch size must be between 1 and 10,000.")
        if self.max_queue_depth < self.batch_size or self.max_queue_depth > 50000:
            raise ValueError("Queue depth must be between batch size and 50,000.")
        if self.heartbeat_interval_seconds < 0.1 or self.heartbeat_interval_seconds > 60.0:
            raise ValueError("Heartbeat interval must be between 0.1 and 60.0 seconds.")
        if self.retry_limit < 0 or self.retry_limit > 10:
            raise ValueError("Retry limit must be between 0 and 10.")

@dataclass(frozen=True)
class CDCEvent:
    event_id: str
    tx_id: str
    timestamp: datetime
    operation: CDCOperationType
    schema_name: str
    table_name: str
    primary_key_values: Dict[str, Any]
    before_image: Optional[Dict[str, Any]] = None
    after_image: Optional[Dict[str, Any]] = None
    lsn_offset: Optional[int] = None
    checksum: str = ""

@dataclass(frozen=True)
class CDCCheckpoint:
    session_id: str
    last_processed_event_id: str
    last_processed_lsn: int
    last_processed_tx_id: str
    last_processed_timestamp: datetime
    adapter_state: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SynchronizationMetrics:
    events_processed: int = 0
    bytes_processed: int = 0
    queue_depth: int = 0
    conflict_count: int = 0
    retry_count: int = 0
    lag_seconds: float = 0.0

@dataclass
class SynchronizationHealth:
    is_healthy: bool = True
    last_heartbeat: Optional[datetime] = None
    last_error_message: str = ""
    degraded_state: bool = False

@dataclass
class SynchronizationSession:
    session_id: str
    configuration: SynchronizationConfiguration
    state: CDCSessionState
    checkpoint: CDCCheckpoint
    metrics: SynchronizationMetrics
    health: SynchronizationHealth
