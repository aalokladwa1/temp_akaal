"""
akaalEngine.telemetry.models.metric
====================================
Canonical Metric models, types, descriptors, and snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence


class MetricType(str, Enum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    RATE_TIMER = "RATE_TIMER"


@dataclass(frozen=True)
class MetricDescriptor:
    """Metric registration descriptor."""
    name: str
    metric_type: MetricType
    description: str
    unit: str = ""
    allowed_labels: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class MetricValue:
    """Immutable single metric sample value with labels."""
    name: str
    metric_type: MetricType
    value: float
    labels: Mapping[str, str] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass(frozen=True)
class MetricSnapshot:
    """Immutable snapshot of all metric series."""
    timestamp: float
    counters: Dict[str, float]
    gauges: Dict[str, float]
    histograms: Dict[str, Dict[str, float]]
    rate_timers: Dict[str, Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": self.histograms,
            "rate_timers": self.rate_timers,
        }
