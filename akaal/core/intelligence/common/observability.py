"""
Akaal — Telemetry and Observability Contracts
=============================================
Defines the telemetry contexts, timing records, metric tracking models,
and telemetry interfaces for the Migration Intelligence platform.
"""

import abc
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from akaal.core.intelligence.common.exceptions import ObservabilityError


@dataclass(frozen=True)
class TelemetryContext:
    """Immutable diagnostic tracing boundaries."""
    correlation_id: str
    trace_id: str
    request_id: str
    migration_id: str
    replay_id: Optional[str] = None


@dataclass(frozen=True)
class MetricRecord:
    """Immutable representation of a recorded counter or gauge metric."""
    subsystem: str
    category: str
    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EventRecord:
    """Immutable representation of a recorded system event."""
    subsystem: str
    event_category: str
    event_name: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class TimingRecord:
    """Immutable representation of a recorded duration metric."""
    subsystem: str
    operation: str
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ITelemetryExporter(abc.ABC):
    """Interface for shipping captured telemetry data."""
    @abc.abstractmethod
    def export_metric(self, context: TelemetryContext, record: MetricRecord) -> None:
        pass

    @abc.abstractmethod
    def export_event(self, context: TelemetryContext, record: EventRecord) -> None:
        pass

    @abc.abstractmethod
    def export_timing(self, context: TelemetryContext, record: TimingRecord) -> None:
        pass


class MemoryTelemetryExporter(ITelemetryExporter):
    """In-memory telemetry exporter for assertion, validation, and testing."""
    def __init__(self) -> None:
        self.metrics: List[Tuple[TelemetryContext, MetricRecord]] = []
        self.events: List[Tuple[TelemetryContext, EventRecord]] = []
        self.timings: List[Tuple[TelemetryContext, TimingRecord]] = []

    def export_metric(self, context: TelemetryContext, record: MetricRecord) -> None:
        self.metrics.append((context, record))

    def export_event(self, context: TelemetryContext, record: EventRecord) -> None:
        self.events.append((context, record))

    def export_timing(self, context: TelemetryContext, record: TimingRecord) -> None:
        self.timings.append((context, record))

    def clear(self) -> None:
        """Flushes all stored records."""
        self.metrics.clear()
        self.events.clear()
        self.timings.clear()


class IIntelligenceObservability(abc.ABC):
    """Interface for recording telemetry across subsystems."""
    @abc.abstractmethod
    def record_metric(self, category: str, name: str, value: float) -> None:
        pass

    @abc.abstractmethod
    def record_event(self, event_category: str, event_name: str, payload: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def record_duration(self, operation: str, duration_ms: float) -> None:
        pass


class IntelligenceObservabilityContext(IIntelligenceObservability):
    """Concrete implementation of observability metrics collector."""
    def __init__(
        self,
        subsystem_id: str,
        context: TelemetryContext,
        exporter: ITelemetryExporter
    ) -> None:
        if not subsystem_id:
            raise ObservabilityError("Subsystem ID must not be empty", error_code="OBS_ERR_EMPTY_SUBSYSTEM")
        self.subsystem_id = subsystem_id
        self.context = context
        self.exporter = exporter

    def record_metric(self, category: str, name: str, value: float) -> None:
        record = MetricRecord(
            subsystem=self.subsystem_id,
            category=category,
            name=name,
            value=value
        )
        self.exporter.export_metric(self.context, record)

    def record_event(self, event_category: str, event_name: str, payload: Dict[str, Any]) -> None:
        record = EventRecord(
            subsystem=self.subsystem_id,
            event_category=event_category,
            event_name=event_name,
            payload=payload
        )
        self.exporter.export_event(self.context, record)

    def record_duration(self, operation: str, duration_ms: float) -> None:
        record = TimingRecord(
            subsystem=self.subsystem_id,
            operation=operation,
            duration_ms=duration_ms
        )
        self.exporter.export_timing(self.context, record)


class TimingTracker:
    """Context manager to trace execution durations."""
    def __init__(self, obs: IIntelligenceObservability, operation_name: str) -> None:
        self.obs = obs
        self.operation_name = operation_name
        self.start_time: float = 0.0

    def __enter__(self) -> 'TimingTracker':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000.0
        self.obs.record_duration(self.operation_name, duration_ms)
