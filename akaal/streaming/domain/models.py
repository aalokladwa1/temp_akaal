"""
Immutable domain models for Platform 3 - Streaming Execution Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from akaal.streaming.domain.identifiers import (
    StreamId, OperatorId, BatchId, WatermarkId, WindowId
)
from akaal.streaming.domain.enums import WindowType, JoinType


@dataclass(frozen=True)
class StreamRecord:
    """Immutable streaming record holding generic data payload and event timestamp."""
    payload: Dict[str, Any]
    event_time: float
    key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_time < 0:
            raise ValueError("StreamRecord event_time must be non-negative.")


@dataclass(frozen=True)
class Watermark:
    """Immutable Watermark representing progress in event time."""
    timestamp: float
    watermark_id: WatermarkId = field(default_factory=WatermarkId.generate)

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError("Watermark timestamp must be non-negative.")


@dataclass(frozen=True)
class StreamWindow:
    """Immutable StreamWindow interval."""
    window_id: WindowId
    window_type: WindowType
    start_time: float
    end_time: float

    def __post_init__(self) -> None:
        if self.end_time <= self.start_time:
            raise ValueError("StreamWindow end_time must be strictly after start_time.")


@dataclass(frozen=True)
class StreamBatch:
    """Batch of StreamRecords."""
    batch_id: BatchId
    records: List[StreamRecord]
    created_at: float

    def __len__(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class ColumnarBatch:
    """Columnar memory representation of a stream batch."""
    batch_id: BatchId
    num_rows: int
    columns: Dict[str, List[Any]]
    created_at: float

    def __len__(self) -> int:
        return self.num_rows


@dataclass(frozen=True)
class StreamConfig:
    max_buffer_size_mb: float = 128.0
    high_watermark_threshold: float = 0.8
    low_watermark_threshold: float = 0.2
    batch_size: int = 1000
    allowed_lateness_seconds: float = 10.0
    spill_to_disk_enabled: bool = True
