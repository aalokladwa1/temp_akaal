# -*- coding: utf-8 -*-
"""akaal.metrics.metrics

Implementation of metric primitive classes for the metrics subsystem.
Each primitive holds its mutable state in *instance* attributes (no class‑level
state) and protects that state with a dedicated ``threading.Lock``.
Timer is intentionally **not** a subclass of ``_BaseMetric`` – it is a plain
context manager that records elapsed time into a ``Histogram``.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------
# Helper for deterministic label keys
# ---------------------------------------------------------------------
def _freeze_labels(labels: dict | None) -> frozenset:
    """Return a deterministic frozen representation of *labels*.

    ``None`` yields an empty frozenset. The ordering is sorted so that two
    dictionaries with the same items produce the same key.
    """
    if not labels:
        return frozenset()
    return frozenset(sorted(labels.items()))


# ---------------------------------------------------------------------
# Base class – provides name, labels and a lock. No mutable metric state lives
# here; concrete subclasses create their own instance attributes.
# ---------------------------------------------------------------------
@dataclass
class _BaseMetric:
    name: str
    labels: dict | None = None
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _label_key: frozenset = field(init=False)

    def __post_init__(self) -> None:
        self._label_key = _freeze_labels(self.labels)

    def snapshot(self) -> Any:
        """Return a serialisable snapshot of the metric's current state.

        Concrete subclasses must implement this.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------
# Counter – monotonically increasing integer
# ---------------------------------------------------------------------
class Counter(_BaseMetric):
    """Monotonically increasing counter.

    The current value is stored in the private ``_value`` instance attribute.
    """

    def __init__(self, name: str, labels: dict | None = None):
        super().__init__(name=name, labels=labels)
        self._value: int = 0

    def increment(self, delta: int = 1) -> None:
        if delta < 0:
            raise ValueError("Counter cannot be decremented")
        with self._lock:
            self._value += delta

    def get(self) -> int:
        with self._lock:
            return self._value

    def snapshot(self) -> int:
        return self.get()


# ---------------------------------------------------------------------
# Gauge – can move up and down
# ---------------------------------------------------------------------
class Gauge(_BaseMetric):
    """Metric representing a mutable numeric value (e.g., current queue size)."""

    def __init__(self, name: str, labels: dict | None = None):
        super().__init__(name=name, labels=labels)
        self._value: float = 0.0

    def set(self, value: float) -> None:
        with self._lock:
            self._value = float(value)

    def inc(self, delta: float = 1.0) -> None:
        with self._lock:
            self._value += float(delta)

    def dec(self, delta: float = 1.0) -> None:
        with self._lock:
            self._value -= float(delta)

    def get(self) -> float:
        with self._lock:
            return self._value

    def snapshot(self) -> float:
        return self.get()


# ---------------------------------------------------------------------
# Histogram – bounded reservoir sampling for percentiles
# ---------------------------------------------------------------------
class Histogram(_BaseMetric):
    """Tracks distribution of numeric observations.

    Stores simple aggregates (count, sum, min, max) and a **bounded reservoir**
    of random samples for percentile estimation. The reservoir size is
    configurable; the default (256) matches the design specification.

    *Why a bounded reservoir?* The migration engine may record millions of
    latency observations. Keeping all samples would be memory‑intensive.
    Reservoir sampling provides a uniform random subset of the full stream
    using O(reservoir_size) memory. Sorting this small list to compute
    percentiles is cheap (max 256 items) and yields deterministic results.
    """

    def __init__(self, name: str, labels: dict | None = None, reservoir_size: int = 256):
        super().__init__(name=name, labels=labels)
        self.reservoir_size: int = reservoir_size
        self._count: int = 0
        self._sum: float = 0.0
        self._min: float | None = None
        self._max: float | None = None
        self._samples: List[float] = []

    def record(self, value: float) -> None:
        """Record a new observation into the histogram.

        The method updates aggregates and maintains the bounded reservoir via
        *Algorithm R* (reservoir sampling). ``random.randrange`` is used for the
        random index selection because it is marginally faster than ``randint``
        and clearly expresses the half‑open interval.
        """
        v = float(value)
        with self._lock:
            self._count += 1
            self._sum += v
            if self._min is None or v < self._min:
                self._min = v
            if self._max is None or v > self._max:
                self._max = v

            # Reservoir sampling – keep a random subset when full.
            if len(self._samples) < self.reservoir_size:
                self._samples.append(v)
            else:
                # ``self._count`` is the total number of items observed so far.
                idx = random.randrange(0, self._count)
                if idx < self.reservoir_size:
                    self._samples[idx] = v

    # -----------------------------------------------------------------
    # Percentile calculation from the bounded reservoir
    # -----------------------------------------------------------------
    def _percentile(self, p: float) -> float | None:
        """Return the *p*‑th percentile (0‑100) from the reservoir.

        Linear interpolation is used between the two nearest ranks when the
        exact rank is not an integer. If the reservoir is empty ``None`` is
        returned.
        """
        if not self._samples:
            return None
        sorted_samples = sorted(self._samples)
        k = (len(sorted_samples) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(sorted_samples) - 1)
        if f == c:
            return sorted_samples[int(k)]
        # Interpolate between the surrounding samples.
        d0 = sorted_samples[f] * (c - k)
        d1 = sorted_samples[c] * (k - f)
        return d0 + d1

    def snapshot(self) -> Dict[str, Any]:
        """Return a plain dict with aggregates and percentile values."""
        with self._lock:
            return {
                "count": self._count,
                "sum": self._sum,
                "min": self._min,
                "max": self._max,
                "avg": (self._sum / self._count) if self._count else None,
                "p50": self._percentile(50),
                "p90": self._percentile(90),
                "p95": self._percentile(95),
                "p99": self._percentile(99),
                "samples": list(self._samples),
            }


# ---------------------------------------------------------------------
# Timer – plain context manager that records elapsed time into a Histogram
# ---------------------------------------------------------------------
class Timer:
    """Context manager measuring elapsed time and recording it into a ``Histogram``.

    The timer does **not** inherit from ``_BaseMetric`` because it does not
    represent a first‑class metric; it merely provides a convenient way to
    instrument code sections.
    """

    def __init__(self, histogram: Histogram, labels: dict | None = None):
        self._histogram = histogram
        self._labels = labels  # preserved for possible future extensions
        self._start: float | None = None

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        end = time.perf_counter()
        elapsed = (end - self._start) if self._start is not None else 0.0
        try:
            self._histogram.record(elapsed)
        except Exception:
            pass  # Metrics failures must never abort migration
        # Return False to propagate any exception raised inside the with-block
        return False

    # ``Timer`` does not expose a snapshot; its purpose is side‑effect only.


# ---------------------------------------------------------------------
# Rate – derived metric representing a rate (e.g., rows/sec)
# ---------------------------------------------------------------------
class Rate(_BaseMetric):
    """Derived metric representing a rate calculated from a count and elapsed time."""

    def __init__(self, name: str, labels: dict | None = None):
        super().__init__(name=name, labels=labels)
        self._value: float = 0.0

    def observe(self, count: int, elapsed_seconds: float) -> None:
        if elapsed_seconds <= 0:
            raise ValueError("Elapsed time must be positive for Rate calculation")
        with self._lock:
            self._value = count / elapsed_seconds

    def get(self) -> float:
        with self._lock:
            return self._value

    def snapshot(self) -> float:
        return self.get()

# End of metrics.py
