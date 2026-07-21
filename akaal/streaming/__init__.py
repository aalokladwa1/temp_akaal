"""
Akaal Platform 3 - Streaming Execution Engine Package.
Generic, zero-copy, event-time streaming execution engine.
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
from akaal.streaming.memory.buffer import BufferOwner, MemorySlice, StreamBuffer
from akaal.streaming.memory.pool import StreamMemoryPool
from akaal.streaming.memory.columnar import ColumnarMemoryPipeline
from akaal.streaming.time.watermark import (
    EventTimeExtractor, DefaultEventTimeExtractor, WatermarkGenerator, BoundedOutOfOrdernessWatermark
)
from akaal.streaming.time.lateness import AllowedLateness
from akaal.streaming.windowing.assigner import (
    WindowAssigner, TumblingWindowAssigner, SlidingWindowAssigner, SessionWindowAssigner
)
from akaal.streaming.windowing.operator import WindowOperator
from akaal.streaming.operators.base import StreamOperator, MapOperator, FilterOperator
from akaal.streaming.operators.join import StreamStreamJoinOperator
from akaal.streaming.operators.fusion import FusedStreamOperator, StreamGraphOptimizer
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.streaming.flow.adaptive import AdaptiveStreamTuner
from akaal.streaming.engine.streaming_engine import StreamingExecutionEngine
from akaal.streaming.facade.runtime import StreamingRuntimeV1, DefaultStreamingRuntimeV1

__all__ = [
    "StreamId", "OperatorId", "BatchId", "WatermarkId", "WindowId",
    "StreamOperatorType", "WindowType", "JoinType", "BackpressureState",
    "StreamingExecutionError", "BackpressureError", "MemoryExhaustedError", "WatermarkError", "WindowingError",
    "StreamRecord", "Watermark", "StreamWindow", "StreamBatch", "ColumnarBatch", "StreamConfig",
    "BufferOwner", "MemorySlice", "StreamBuffer",
    "StreamMemoryPool", "ColumnarMemoryPipeline",
    "EventTimeExtractor", "DefaultEventTimeExtractor", "WatermarkGenerator", "BoundedOutOfOrdernessWatermark",
    "AllowedLateness",
    "WindowAssigner", "TumblingWindowAssigner", "SlidingWindowAssigner", "SessionWindowAssigner",
    "WindowOperator",
    "StreamOperator", "MapOperator", "FilterOperator",
    "StreamStreamJoinOperator", "FusedStreamOperator", "StreamGraphOptimizer",
    "BackpressureController", "AdaptiveStreamTuner",
    "StreamingExecutionEngine",
    "StreamingRuntimeV1", "DefaultStreamingRuntimeV1",
]
