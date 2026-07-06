# -*- coding: utf-8 -*-
"""akaal.metrics.registry

Core registry for the metrics subsystem. The registry owns all metric
instances, provides thread‑safe registration, and can snapshot the current
state into an immutable :class:`MetricsSnapshot`.

Lock hierarchy
--------------
* **Registry lock (RLock)** – protects the internal ``_metrics`` mapping.
* **Metric lock (Lock)** – each metric primitive protects its own mutable
  state. When taking a snapshot the registry iterates over the registered
  metrics, acquiring each metric's lock individually. This minimises contention
  because the registry lock is held only for the brief copy of the mapping.

Ownership model
---------------
``MigrationSession`` creates an ``ObservabilityContext`` which owns a single
``MetricsRegistry`` instance. All components (Pipeline, ManagerAgent, GBAgent,
etc.) receive the registry via dependency injection, ensuring a clear
single‑owner relationship and avoiding global singletons.
"""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import Any, Dict, Tuple

from .summary import MetricsSnapshot


class MetricsRegistry:
    """Thread‑safe container for metric primitives.

    The registry holds a mapping from a *metric key* (a tuple of the metric name
    and its frozen label set) to the concrete metric instance. Metric instances
    manage their own internal locking; the registry only guards registration.
    """

    def __init__(self) -> None:
        self._registry_lock = threading.RLock()
        self._metrics: Dict[Tuple[str, frozenset], Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers (private)
    # ---------------------------------------------------------------------
    def _freeze_labels(self, labels: dict | None) -> frozenset:
        return frozenset(sorted(labels.items())) if labels else frozenset()

    def _register(self, name: str, metric: Any, labels: dict | None = None) -> None:
        """Register *metric* under *name* with optional *labels*.

        Raises ``KeyError`` if a metric with the same key already exists.
        """
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            if key in self._metrics:
                raise KeyError(f"Metric {name} with labels {labels} already registered")
            self._metrics[key] = metric

    def _get(self, name: str, labels: dict | None = None) -> Any | None:
        """Retrieve a metric by *name* and optional *labels* (private)."""
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            return self._metrics.get(key)

    # ---------------------------------------------------------------------
    # Private creation helpers – used by the public convenience API
    # ---------------------------------------------------------------------
    def _get_or_create_counter(self, name: str, labels: dict | None = None):
        from .metrics import Counter
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, Counter):
                    return existing
                raise TypeError("Existing metric under the same key is not a Counter")
            counter = Counter(name=name, labels=labels)
            self._metrics[key] = counter
            return counter

    def _get_or_create_gauge(self, name: str, labels: dict | None = None):
        from .metrics import Gauge
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, Gauge):
                    return existing
                raise TypeError("Existing metric under the same key is not a Gauge")
            gauge = Gauge(name=name, labels=labels)
            self._metrics[key] = gauge
            return gauge

    def _get_or_create_histogram(self, name: str, labels: dict | None = None, reservoir_size: int = 256):
        from .metrics import Histogram
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, Histogram):
                    return existing
                raise TypeError("Existing metric under the same key is not a Histogram")
            histogram = Histogram(name=name, labels=labels, reservoir_size=reservoir_size)
            self._metrics[key] = histogram
            return histogram

    def _get_or_create_rate(self, name: str, labels: dict | None = None):
        from .metrics import Rate
        key = (name, self._freeze_labels(labels))
        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, Rate):
                    return existing
                raise TypeError("Existing metric under the same key is not a Rate")
            rate = Rate(name=name, labels=labels)
            self._metrics[key] = rate
            return rate

    # ---------------------------------------------------------------------
    # Public API – convenience getters
    # ---------------------------------------------------------------------
    def counter(self, name: str, labels: dict | None = None):
        """Return a :class:`Counter` for *name* (create if missing)."""
        return self._get_or_create_counter(name, labels)

    def gauge(self, name: str, labels: dict | None = None):
        """Return a :class:`Gauge` for *name* (create if missing)."""
        return self._get_or_create_gauge(name, labels)

    def histogram(self, name: str, labels: dict | None = None, reservoir_size: int = 256):
        """Return a :class:`Histogram` for *name* (create if missing)."""
        return self._get_or_create_histogram(name, labels, reservoir_size)

    def rate(self, name: str, labels: dict | None = None):
        """Return a :class:`Rate` for *name* (create if missing)."""
        return self._get_or_create_rate(name, labels)

    def timer(self, name: str, labels: dict | None = None, reservoir_size: int = 256):
        """Create a :class:`Timer` that records into a histogram with *name*.

        The underlying histogram is created (or retrieved) automatically.
        """
        from .metrics import Timer
        histogram = self._get_or_create_histogram(name, labels, reservoir_size)
        return Timer(histogram=histogram, labels=labels)

    # ---------------------------------------------------------------------
    # Snapshot – returns an immutable snapshot of all registered metrics
    # ---------------------------------------------------------------------
    def snapshot(self) -> MetricsSnapshot:
        """Create an immutable snapshot of all registered metrics.

        Each metric's own ``snapshot`` method is called while holding its lock.
        The resulting mapping is wrapped in a ``MappingProxyType`` to guarantee
        immutability.
        """
        with self._registry_lock:
            metrics_copy = dict(self._metrics)
        snapshot_data: Dict[Tuple[str, frozenset], Any] = {}
        for (name, label_key), metric in metrics_copy.items():
            snapshot_data[(name, label_key)] = metric.snapshot()
        # Make the dict read‑only.
        immutable_data = MappingProxyType(snapshot_data)
        return MetricsSnapshot(data=immutable_data)

    # ---------------------------------------------------------------------
    # Reset – test‑only helper
    # ---------------------------------------------------------------------
    def reset(self) -> None:
        """Clear all registered metrics (used by unit tests)."""
        with self._registry_lock:
            self._metrics.clear()
