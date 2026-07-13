# -*- coding: utf-8 -*-
"""akaal.metrics

Public API for the metrics subsystem.

Ownership model
---------------
    MigrationSession
        └── ObservabilityContext
                └── MetricsRegistry   ← one instance per migration
                        ├── Counter
                        ├── Gauge
                        ├── Histogram (+ Timer helper)
                        └── Rate

Components receive ``MetricsRegistry`` via dependency injection.
There is no global singleton.
"""

from __future__ import annotations

# Metric name constants – use these everywhere instead of raw strings.
from .constants import (
    MIGRATION_DURATION,
    ROWS_MIGRATED,
    BYTES_MIGRATED,
    TABLES_MIGRATED,
)

# Core registry
from .registry import MetricsRegistry

# Metric primitives
from .metrics import Counter, Gauge, Histogram, Timer, Rate

# Snapshot / summary
from .summary import MetricsSnapshot, MigrationSummary, SummaryGenerator

# Exporter abstraction
from .exporter import MetricsExporter

__all__ = [
    # Constants
    "MIGRATION_DURATION",
    "ROWS_MIGRATED",
    "BYTES_MIGRATED",
    "TABLES_MIGRATED",
    # Registry
    "MetricsRegistry",
    # Primitives
    "Counter",
    "Gauge",
    "Histogram",
    "Timer",
    "Rate",
    # Snapshot / summary
    "MetricsSnapshot",
    "MigrationSummary",
    "SummaryGenerator",
    # Exporter
    "MetricsExporter",
]
