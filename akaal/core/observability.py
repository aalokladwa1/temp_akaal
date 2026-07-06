# -*- coding: utf-8 -*-
"""akaal.core.observability

ObservabilityContext — lightweight container owned by MigrationSession.

Ownership model
---------------
    MigrationSession
        └── ObservabilityContext        ← created once, lives exactly as long as the session
                ├── MetricsRegistry     ← one registry per migration
                └── trace (None)        ← placeholder for Phase 7L distributed tracing

Design rules
------------
* This module does NOT import anything from ``akaal.logging_manager``.
  Logging context propagation remains entirely in the logging subsystem.
* This module does NOT import ``SummaryGenerator`` or any exporter.
  Summary generation is performed by the Pipeline *after* migration completion.
* No global state.  No module-level instances.
"""

from __future__ import annotations

from typing import Any

from akaal.metrics.registry import MetricsRegistry


class ObservabilityContext:
    """Lightweight container that groups observability concerns for a single migration run.

    Components receive ``ObservabilityContext`` (or extract ``registry`` from it) via
    dependency injection. They never construct one themselves.

    Attributes
    ----------
    registry : MetricsRegistry
        The single metrics registry for this migration. Its lifetime equals that
        of the owning ``MigrationSession``.
    trace : Any | None
        Placeholder for a distributed-tracing span/context to be populated in
        Phase 7L. Callers may safely ignore this attribute until that phase.
    """

    __slots__ = ("registry", "trace", "baggage")

    def __init__(self) -> None:
        self.registry: MetricsRegistry = MetricsRegistry()
        self.trace: Any | None = None
        self.baggage: Any | None = None  # Placeholder for future OpenTelemetry context propagation
