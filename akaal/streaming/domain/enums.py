"""
Domain Enums for Platform 3 - Streaming Execution Engine.
"""

from enum import Enum


class StreamOperatorType(str, Enum):
    SOURCE = "SOURCE"
    MAP = "MAP"
    FILTER = "FILTER"
    WINDOW = "WINDOW"
    JOIN = "JOIN"
    FUSED = "FUSED"
    SINK = "SINK"


class WindowType(str, Enum):
    TUMBLING = "TUMBLING"
    SLIDING = "SLIDING"
    SESSION = "SESSION"
    CUSTOM = "CUSTOM"


class JoinType(str, Enum):
    INNER = "INNER"
    LEFT_OUTER = "LEFT_OUTER"
    RIGHT_OUTER = "RIGHT_OUTER"
    FULL_OUTER = "FULL_OUTER"


class BackpressureState(str, Enum):
    NORMAL = "NORMAL"
    LOW_WATERMARK = "LOW_WATERMARK"
    HIGH_WATERMARK = "HIGH_WATERMARK"
    THROTTLED = "THROTTLED"
