"""
Domain package for Platform 3 - Streaming Execution Engine.
"""

from akaal.streaming.domain.identifiers import (
    StreamId, OperatorId, BatchId, WatermarkId, WindowId
)
from akaal.streaming.domain.enums import (
    StreamOperatorType, WindowType, JoinType, BackpressureState
)
from akaal.streaming.domain.errors import (
    StreamingExecutionError, BackpressureError, MemoryExhaustedError, WatermarkError, WindowingError
)
from akaal.streaming.domain.models import (
    StreamRecord, Watermark, StreamWindow, StreamBatch, ColumnarBatch, StreamConfig
)

__all__ = [
    "StreamId", "OperatorId", "BatchId", "WatermarkId", "WindowId",
    "StreamOperatorType", "WindowType", "JoinType", "BackpressureState",
    "StreamingExecutionError", "BackpressureError", "MemoryExhaustedError", "WatermarkError", "WindowingError",
    "StreamRecord", "Watermark", "StreamWindow", "StreamBatch", "ColumnarBatch", "StreamConfig",
]
