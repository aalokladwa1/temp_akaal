"""
akaalEngine.telemetry.api
=========================
Single Canonical Entrypoint and Façade for Authority #7 — Telemetry (`TelemetryAuthority`).
"""

import logging
from threading import RLock
from typing import Any, Callable, Dict, List, Mapping, Optional

from akaalEngine.telemetry.bus.context import CorrelationContext
from akaalEngine.telemetry.bus.dispatcher import InProcessEventDispatcher
from akaalEngine.telemetry.exporters.external import OpenTelemetryExporterSeam
from akaalEngine.telemetry.exporters.prometheus import PrometheusTextExporter
from akaalEngine.telemetry.health.evaluator import HealthEvaluator
from akaalEngine.telemetry.logging.logger import StructuredOperationalLogger
from akaalEngine.telemetry.metrics.cardinality import CardinalityGuard
from akaalEngine.telemetry.metrics.registry import MetricsRegistry
from akaalEngine.telemetry.models import (
    ComponentHealth,
    EventMetadata,
    HealthSnapshot,
    HealthState,
    MetricDescriptor,
    MetricSnapshot,
    OperationalEvent,
    ProgressSnapshot,
    UNKNOWN_TOTAL,
)
from akaalEngine.telemetry.progress.tracker import ProgressTracker
from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

logger = logging.getLogger("akaalEngine.telemetry.api")


class TelemetryAuthority:
    """
    Single Canonical Façade for Authority #7 — Telemetry.
    Owns operational event publishing, correlation tracing, metrics collection,
    truthful progress tracking, component health evaluation, secret sanitization,
    and Prometheus/OTel exports.
    """

    def __init__(
        self,
        runtime_authority: Optional[Any] = None,
        max_cardinality_per_metric: int = 100,
        max_history_events: int = 1000,
    ) -> None:
        self.runtime_authority = runtime_authority
        self._lock = RLock()

        # Subsystem initialization
        self.cardinality_guard = CardinalityGuard(max_cardinality_per_metric=max_cardinality_per_metric)
        self.metrics_registry = MetricsRegistry(cardinality_guard=self.cardinality_guard)
        self.event_dispatcher = InProcessEventDispatcher(max_history_events=max_history_events)
        self.progress_tracker = ProgressTracker()
        self.health_evaluator = HealthEvaluator()
        self.structured_logger = StructuredOperationalLogger()
        self.prometheus_exporter = PrometheusTextExporter(self.metrics_registry)
        self.otel_exporter_seam = OpenTelemetryExporterSeam()

    # --- Correlation Context ---
    def set_correlation_context(self, ctx: CorrelationContext) -> None:
        CorrelationContext.set_current(ctx)

    def get_correlation_context(self) -> CorrelationContext:
        return CorrelationContext.get_current()

    # --- Metrics Collection ---
    def record_counter(self, name: str, increment: float = 1.0, labels: Optional[Mapping[str, str]] = None) -> None:
        try:
            self.metrics_registry.record_counter(name, increment=increment, labels=labels)
        except Exception as exc:
            logger.warning(f"[TelemetryAuthority] record_counter error on '{name}': {exc}")

    def set_gauge(self, name: str, value: float, labels: Optional[Mapping[str, str]] = None) -> None:
        try:
            self.metrics_registry.set_gauge(name, value=value, labels=labels)
        except Exception as exc:
            logger.warning(f"[TelemetryAuthority] set_gauge error on '{name}': {exc}")

    def observe_histogram(self, name: str, value: float, labels: Optional[Mapping[str, str]] = None) -> None:
        try:
            self.metrics_registry.observe_histogram(name, value=value, labels=labels)
        except Exception as exc:
            logger.warning(f"[TelemetryAuthority] observe_histogram error on '{name}': {exc}")

    def observe_timer(self, name: str, duration_seconds: float, labels: Optional[Mapping[str, str]] = None) -> None:
        try:
            self.metrics_registry.observe_timer(name, duration_seconds=duration_seconds, labels=labels)
        except Exception as exc:
            logger.warning(f"[TelemetryAuthority] observe_timer error on '{name}': {exc}")

    def get_metric_snapshot(self) -> MetricSnapshot:
        return self.metrics_registry.get_snapshot()

    # --- Operational Events & Subscriptions ---
    def publish_event(self, event: OperationalEvent) -> None:
        try:
            self.event_dispatcher.publish(event)
        except Exception as exc:
            logger.warning(f"[TelemetryAuthority] publish_event error on '{event.name}': {exc}")

    def subscribe(self, callback: Callable[[OperationalEvent], None], event_type: Optional[str] = None) -> str:
        return self.event_dispatcher.subscribe(callback, event_type=event_type)

    def unsubscribe(self, subscription_id: str) -> bool:
        return self.event_dispatcher.unsubscribe(subscription_id)

    def get_event_history(self, limit: Optional[int] = None) -> List[OperationalEvent]:
        return self.event_dispatcher.get_history(limit=limit)

    # --- Progress Tracking ---
    def initialize_migration_progress(
        self,
        migration_id: str,
        objects_total: int = UNKNOWN_TOTAL,
        rows_total: int = UNKNOWN_TOTAL,
        bytes_total: int = UNKNOWN_TOTAL,
        chunks_total: int = UNKNOWN_TOTAL,
    ) -> ProgressSnapshot:
        return self.progress_tracker.initialize_migration(
            migration_id=migration_id,
            objects_total=objects_total,
            rows_total=rows_total,
            bytes_total=bytes_total,
            chunks_total=chunks_total,
        )

    def update_progress(
        self,
        migration_id: str,
        add_objects: int = 0,
        add_rows: int = 0,
        add_bytes: int = 0,
        add_chunks: int = 0,
        rows_total_override: Optional[int] = None,
    ) -> ProgressSnapshot:
        return self.progress_tracker.update_progress(
            migration_id=migration_id,
            add_objects=add_objects,
            add_rows=add_rows,
            add_bytes=add_bytes,
            add_chunks=add_chunks,
            rows_total_override=rows_total_override,
        )

    def get_progress_snapshot(self, migration_id: str) -> ProgressSnapshot:
        return self.progress_tracker.get_snapshot(migration_id)

    # --- Component Health Evaluation ---
    def update_component_health(
        self,
        component: str,
        state: HealthState,
        reason: str = "Operating normally",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ComponentHealth:
        return self.health_evaluator.update_component_health(component, state, reason=reason, metrics=metrics)

    def get_health_snapshot(self) -> HealthSnapshot:
        return self.health_evaluator.get_snapshot()

    # --- Structured Operational Logging ---
    def log_operational(self, level: int, message: str, extra_context: Optional[Dict[str, Any]] = None) -> None:
        self.structured_logger.log(level, message, extra_context=extra_context)

    # --- Exporters ---
    def export_prometheus_text(self) -> str:
        return self.prometheus_exporter.export_text()

    def get_otel_status(self) -> Dict[str, Any]:
        return self.otel_exporter_seam.get_status()

    # --- Authority #6 Runtime Observation ---
    def get_runtime_telemetry_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            runtime_snap = {}
            if self.runtime_authority and hasattr(self.runtime_authority, "get_runtime_snapshot"):
                try:
                    runtime_snap = self.runtime_authority.get_runtime_snapshot()
                except Exception as exc:
                    logger.warning(f"[TelemetryAuthority] Failed to sample Runtime Authority: {exc}")

            metrics_snap = self.get_metric_snapshot().to_dict()
            health_snap = self.get_health_snapshot().to_dict()

            return {
                "runtime_snapshot": runtime_snap,
                "metrics_snapshot": metrics_snap,
                "health_snapshot": health_snap,
                "bus_metrics": self.event_dispatcher.metrics,
                "otel_status": self.get_otel_status(),
            }

    def flush(self) -> None:
        with self._lock:
            logger.info("[TelemetryAuthority] Telemetry Authority flushed successfully.")
