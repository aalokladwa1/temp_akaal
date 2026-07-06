# -*- coding: utf-8 -*-
"""akaal.metrics.summary

Immutable snapshot and high‑level summary objects for the metrics subsystem.
The snapshot captures the raw state of every registered metric at a point in
time. ``SummaryGenerator`` consumes a snapshot and produces a ``MigrationSummary``
that aggregates derived values such as rates and totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Tuple

# Import metric name constants for decoupled reference.
from .constants import (
    MIGRATION_DURATION,
    ROWS_MIGRATED,
    BYTES_MIGRATED,
    TABLES_MIGRATED,
)


@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable container for a snapshot of all metrics.

    ``data`` maps a ``(metric_name, frozen_label_set)`` tuple to the concrete
    snapshot returned by each metric primitive. The underlying mapping is a
    ``MappingProxyType`` to guarantee read‑only access.
    """

    data: MappingProxyType

    def get(self, name: str, labels: dict | None = None) -> Any | None:
        """Retrieve a metric snapshot by *name* and optional *labels*.

        Returns ``None`` if the metric was not present in the snapshot.
        """
        key = (name, frozenset(sorted(labels.items())) if labels else frozenset())
        return self.data.get(key)


@dataclass(frozen=True)
class MigrationSummary:
    """Aggregated, human‑readable performance summary for a migration run.

    Fields correspond to the high‑level metrics described in the design doc.
    Values are rounded according to the ``metrics_precision`` configuration when
    the summary is generated.
    """

    duration_seconds: float
    rows_migrated: int
    bytes_migrated: int
    tables_migrated: int
    rows_per_sec: float | None = None
    mb_per_sec: float | None = None
    # Additional optional fields can be added later without breaking callers.


class SummaryGenerator:
    """Generate a :class:`MigrationSummary` from a :class:`MetricsSnapshot`.

    The generator uses centrally defined metric name constants to avoid hard‑
    coded strings.
    """

    def __init__(self, precision: int = 2) -> None:
        self._precision = precision

    def generate(self, snapshot: MetricsSnapshot) -> MigrationSummary:
        # Helper to fetch counter values safely.
        def _counter(name: str, labels: dict | None = None) -> int:
            val = snapshot.get(name, labels)
            return int(val) if isinstance(val, (int, float)) else 0

        # Helper to fetch histogram aggregates.
        def _histogram(name: str, labels: dict | None = None) -> Dict[str, Any] | None:
            return snapshot.get(name, labels)

        rows = _counter(ROWS_MIGRATED)
        bytes_ = _counter(BYTES_MIGRATED)
        tables = _counter(TABLES_MIGRATED)
        duration_hist = _histogram(MIGRATION_DURATION)
        duration = duration_hist.get("sum") if duration_hist else 0.0

        rows_per_sec = (rows / duration) if duration > 0 else None
        mb_per_sec = (bytes_ / (1024 * 1024) / duration) if duration > 0 else None

        # Apply precision rounding.
        if rows_per_sec is not None:
            rows_per_sec = round(rows_per_sec, self._precision)
        if mb_per_sec is not None:
            mb_per_sec = round(mb_per_sec, self._precision)

        return MigrationSummary(
            duration_seconds=round(duration, self._precision),
            rows_migrated=rows,
            bytes_migrated=bytes_,
            tables_migrated=tables,
            rows_per_sec=rows_per_sec,
            mb_per_sec=mb_per_sec,
        )

# End of summary.py
