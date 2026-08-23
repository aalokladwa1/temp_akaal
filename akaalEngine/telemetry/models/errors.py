"""
akaalEngine.telemetry.models.errors
====================================
Typed exception hierarchy for Authority #7 Telemetry.
"""

from typing import Any, Mapping, Optional


class TelemetryEngineException(Exception):
    """Base exception for all Authority #7 Telemetry errors."""

    def __init__(self, message: str, error_code: str = "TELEMETRY_ERROR", details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class MetricCardinalityExceededError(TelemetryEngineException):
    """Raised when metric label combination exceeds cardinality bounds."""
    def __init__(self, metric_name: str, max_cardinality: int) -> None:
        super().__init__(
            f"Metric '{metric_name}' exceeded maximum allowed label cardinality ({max_cardinality}).",
            error_code="CARDINALITY_EXCEEDED",
            details={"metric_name": metric_name, "max_cardinality": max_cardinality},
        )


class InvalidMetricValueError(TelemetryEngineException):
    """Raised when a metric value is invalid (e.g., negative counter increment)."""
    def __init__(self, metric_name: str, value: Any, reason: str) -> None:
        super().__init__(
            f"Invalid value '{value}' for metric '{metric_name}': {reason}",
            error_code="INVALID_METRIC_VALUE",
            details={"metric_name": metric_name, "value": value, "reason": reason},
        )


class TelemetrySubscriberError(TelemetryEngineException):
    """Raised when an event subscriber fails during dispatch."""
    def __init__(self, subscriber_name: str, event_type: str, cause: str) -> None:
        super().__init__(
            f"Subscriber '{subscriber_name}' failed on event '{event_type}': {cause}",
            error_code="SUBSCRIBER_ERROR",
            details={"subscriber_name": subscriber_name, "event_type": event_type, "cause": cause},
        )
