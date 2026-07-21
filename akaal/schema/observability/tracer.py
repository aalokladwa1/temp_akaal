"""
AKAAL Platform 5 — Observability SchemaTracer

Provides correlation ID, transaction ID, and span ID tracing across all operations.
"""

from dataclasses import dataclass, field
import threading

_trace_context = threading.local()


@dataclass
class TraceContext:
    trace_id: str
    correlation_id: str
    tx_id: str = ""
    span_id: str = ""


class SchemaTracer:
    """Thread-safe context tracer emitting correlation IDs across schema evolution operations."""

    @staticmethod
    def get_current_context() -> TraceContext:
        if not hasattr(_trace_context, "ctx"):
            _trace_context.ctx = TraceContext(
                trace_id="tr-default", correlation_id="corr-default"
            )
        return _trace_context.ctx

    @staticmethod
    def set_context(trace_id: str, correlation_id: str, tx_id: str = "") -> TraceContext:
        ctx = TraceContext(trace_id=trace_id, correlation_id=correlation_id, tx_id=tx_id)
        _trace_context.ctx = ctx
        return ctx

    @staticmethod
    def clear_context() -> None:
        if hasattr(_trace_context, "ctx"):
            del _trace_context.ctx
