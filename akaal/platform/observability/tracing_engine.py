"""
OpenTelemetry Distributed Tracing & W3C Trace Context Propagator.
"""

from dataclasses import dataclass, field
import threading
import time
import uuid
from typing import Dict, List, Optional


@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time_ms: int
    end_time_ms: Optional[int] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    status: str = "OK"

    def finish(self) -> None:
        self.end_time_ms = int(time.time() * 1000)


class TraceContext:
    """W3C compliant trace context carrier."""

    def __init__(self, trace_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex
        self.parent_span_id = parent_span_id

    def inject_headers(self) -> Dict[str, str]:
        return {"traceparent": f"00-{self.trace_id}-{self.parent_span_id or '0000000000000000'}-01"}

    @classmethod
    def extract_headers(cls, headers: Dict[str, str]) -> "TraceContext":
        tp = headers.get("traceparent", "")
        parts = tp.split("-")
        if len(parts) >= 3:
            return cls(trace_id=parts[1], parent_span_id=parts[2])
        return cls()


class TracingEngine:
    """Distributed tracing manager recording spans and trace graphs."""

    def __init__(self) -> None:
        self._spans: List[TraceSpan] = []
        self._lock = threading.Lock()

    def start_span(self, name: str, context: Optional[TraceContext] = None) -> TraceSpan:
        ctx = context or TraceContext()
        span_id = uuid.uuid4().hex[:16]
        span = TraceSpan(
            span_id=span_id,
            trace_id=ctx.trace_id,
            parent_span_id=ctx.parent_span_id,
            name=name,
            start_time_ms=int(time.time() * 1000),
        )
        with self._lock:
            self._spans.append(span)
        return span

    def get_spans_for_trace(self, trace_id: str) -> List[TraceSpan]:
        with self._lock:
            return [s for s in self._spans if s.trace_id == trace_id]
