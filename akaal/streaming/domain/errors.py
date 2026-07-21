"""
Platform 3 Exception Hierarchy.
"""

from typing import Optional, Any


class StreamingExecutionError(Exception):
    """Base exception class for Platform 3 Streaming Execution Engine."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BackpressureError(StreamingExecutionError):
    """Raised when backpressure threshold or buffer bounds are exceeded."""
    pass


class MemoryExhaustedError(StreamingExecutionError):
    """Raised when streaming memory pool capacity is exhausted and spill failed."""
    pass


class WatermarkError(StreamingExecutionError):
    """Raised on invalid watermark regression or timestamp extraction failures."""
    pass


class WindowingError(StreamingExecutionError):
    """Raised on window assignment or aggregation errors."""
    pass
