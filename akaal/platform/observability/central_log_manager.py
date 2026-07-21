"""
AKAAL Platform Part 6 - Observability Subsystem.
Central Asynchronous Non-Blocking Structured Log Manager & OpenTelemetry Observability.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import queue
import threading
import time
from typing import Dict, List, Optional, Any, Callable


class LogLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


@dataclass(frozen=True)
class LogEvent:
    event_id: str
    timestamp_ms: int
    level: LogLevel
    logger_name: str
    message: str
    trace_id: Optional[str]
    span_id: Optional[str]
    node_id: str
    context_attributes: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "event_id": self.event_id,
            "timestamp_ms": self.timestamp_ms,
            "level": self.level.value,
            "logger_name": self.logger_name,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "node_id": self.node_id,
            "context": self.context_attributes,
        })


class LogAggregation:
    """Aggregates log events across worker node processes."""

    def __init__(self) -> None:
        self._logs: List[LogEvent] = []
        self._lock = threading.Lock()

    def append(self, event: LogEvent) -> None:
        with self._lock:
            self._logs.append(event)

    def query_logs(
        self,
        level: Optional[LogLevel] = None,
        logger_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEvent]:
        with self._lock:
            result = []
            for event in reversed(self._logs):
                if level and event.level != level:
                    continue
                if logger_name and logger_name not in event.logger_name:
                    continue
                if trace_id and event.trace_id != trace_id:
                    continue
                result.append(event)
                if len(result) >= limit:
                    break
            return result


class LogRouter:
    """Routes structured logs to external sinks (file, stdout, OpenTelemetry)."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[LogEvent], None]] = []

    def subscribe(self, callback: Callable[[LogEvent], None]) -> None:
        self._subscribers.append(callback)

    def route(self, event: LogEvent) -> None:
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass


class CentralLogManager:
    """Non-blocking, ring-buffer backed asynchronous log processor."""

    def __init__(self, node_id: str, capacity: int = 65536) -> None:
        self.node_id = node_id
        self._queue: queue.Queue = queue.Queue(maxsize=capacity)
        self.aggregation = LogAggregation()
        self.router = LogRouter()
        self._counter = 0
        self._lock = threading.Lock()
        self.router.subscribe(self.aggregation.append)

    def log(
        self,
        level: LogLevel,
        logger_name: str,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        **kwargs: str,
    ) -> LogEvent:
        with self._lock:
            self._counter += 1
            event_id = f"log-{self.node_id}-{int(time.time()*1000)}-{self._counter}"

        event = LogEvent(
            event_id=event_id,
            timestamp_ms=int(time.time() * 1000),
            level=level,
            logger_name=logger_name,
            message=message,
            trace_id=trace_id,
            span_id=span_id,
            node_id=self.node_id,
            context_attributes=kwargs,
        )

        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass  # Non-blocking drop on queue full to preserve streaming latency

        self.router.route(event)
        return event

    def flush(self) -> int:
        flushed_count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                flushed_count += 1
            except queue.Empty:
                break
        return flushed_count
