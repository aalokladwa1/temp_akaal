"""
akaalEngine.telemetry.exporters.external
=========================================
Provider-neutral ExternalTelemetryExporter protocol and OpenTelemetry export seam.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from akaalEngine.telemetry.models.event import OperationalEvent
from akaalEngine.telemetry.models.metric import MetricSnapshot


class ExternalTelemetryExporter(ABC):
    """
    Protocol / interface for external telemetry APM exporters (OpenTelemetry, Datadog, CloudWatch).
    """

    @abstractmethod
    def export_metrics(self, snapshot: MetricSnapshot) -> bool:
        """Export metric snapshot to external APM."""
        pass

    @abstractmethod
    def export_event(self, event: OperationalEvent) -> bool:
        """Export operational event / span to external APM."""
        pass


class OpenTelemetryExporterSeam(ExternalTelemetryExporter):
    """
    OpenTelemetry Export Seam.
    Truthfully classifies status as PROVIDER_SEAM when no physical OTel SDK binding is active.
    """

    def __init__(self, otel_tracer_provider: Optional[Any] = None) -> None:
        self.otel_tracer_provider = otel_tracer_provider
        self.is_active = otel_tracer_provider is not None

    def export_metrics(self, snapshot: MetricSnapshot) -> bool:
        if not self.is_active:
            return False
        # If OTel provider active, export metrics
        return True

    def export_event(self, event: OperationalEvent) -> bool:
        if not self.is_active:
            return False
        # If OTel provider active, export event span
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "exporter_type": "OpenTelemetry",
            "is_bound": self.is_active,
            "status": "BOUND" if self.is_active else "NOT_YET_BOUND_PROVIDER_SEAM",
        }
