"""
Master Observability Manager coordinating Central Log Manager, Metrics Engine, and Tracing Engine.
"""

from typing import Dict, Optional, Any
from akaal.platform.observability.central_log_manager import CentralLogManager, LogLevel, LogEvent
from akaal.platform.observability.metrics_engine import MetricsEngine, MetricsRegistry
from akaal.platform.observability.tracing_engine import TracingEngine, TraceSpan, TraceContext
from akaal.platform.observability.profiling_engine import ProfilingEngine, ObservabilityDashboard


class ObservabilityManager:
    """Master controller orchestrating complete telemetry across all platform components."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.log_manager = CentralLogManager(node_id)
        self.metrics_registry = MetricsRegistry()
        self.metrics_engine = MetricsEngine(self.metrics_registry)
        self.tracing_engine = TracingEngine()
        self.profiling_engine = ProfilingEngine()
        self.dashboard = ObservabilityDashboard()

    def record_counter(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> float:
        return self.metrics_registry.increment_counter(name, amount, labels)

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> float:
        return self.metrics_registry.set_gauge(name, value, labels)

    def start_trace(self, span_name: str, context: Optional[TraceContext] = None) -> TraceSpan:
        return self.tracing_engine.start_span(span_name, context)

    def log_info(self, logger_name: str, message: str, trace_id: Optional[str] = None, **kwargs: str) -> LogEvent:
        return self.log_manager.log(LogLevel.INFO, logger_name, message, trace_id=trace_id, **kwargs)

    def log_error(self, logger_name: str, message: str, trace_id: Optional[str] = None, **kwargs: str) -> LogEvent:
        return self.log_manager.log(LogLevel.ERROR, logger_name, message, trace_id=trace_id, **kwargs)
