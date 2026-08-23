"""
akaalEngine.telemetry
======================
Canonical Telemetry Authority (#7).
Exposes TelemetryAuthority, OperationalEvent, EventMetadata, CorrelationContext,
ProgressSnapshot, HealthSnapshot, HealthState, MetricSnapshot, MetricType, MetricValue.
"""

from akaalEngine.telemetry.api import TelemetryAuthority
from akaalEngine.telemetry.bus.context import CorrelationContext
from akaalEngine.telemetry.models import (
    UNKNOWN_TOTAL,
    ComponentHealth,
    EventMetadata,
    HealthSnapshot,
    HealthState,
    InvalidMetricValueError,
    MetricCardinalityExceededError,
    MetricDescriptor,
    MetricSnapshot,
    MetricType,
    MetricValue,
    OperationalEvent,
    ProgressSnapshot,
    TelemetryEngineException,
    TelemetrySubscriberError,
)
from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

__all__ = [
    "TelemetryAuthority",
    "CorrelationContext",
    "EventMetadata",
    "OperationalEvent",
    "MetricType",
    "MetricDescriptor",
    "MetricValue",
    "MetricSnapshot",
    "UNKNOWN_TOTAL",
    "ProgressSnapshot",
    "HealthState",
    "ComponentHealth",
    "HealthSnapshot",
    "TelemetrySanitizer",
    "TelemetryEngineException",
    "MetricCardinalityExceededError",
    "InvalidMetricValueError",
    "TelemetrySubscriberError",
]
