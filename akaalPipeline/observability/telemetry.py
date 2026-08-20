"""akaalPipeline.observability.telemetry
========================================
Telemetry observations and metrics for monitoring.
Telemetry NEVER mutates or dictates canonical aggregate lifecycle state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Mapping

logger = logging.getLogger("akaalPipeline.telemetry")


@dataclass(frozen=True)
class MetricObservation:
    name: str
    value: float
    unit: str
    tags: Mapping[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PipelineTelemetry:
    def __init__(self) -> None:
        self._observations: List[MetricObservation] = []

    def record_counter(self, name: str, value: float = 1.0, tags: Mapping[str, str] = None) -> None:
        obs = MetricObservation(name=name, value=value, unit="count", tags=dict(tags or {}))
        self._observations.append(obs)
        logger.debug(f"[Telemetry Counter] {name}={value} tags={tags}")

    def record_timing(self, name: str, duration_ms: float, tags: Mapping[str, str] = None) -> None:
        obs = MetricObservation(name=name, value=duration_ms, unit="ms", tags=dict(tags or {}))
        self._observations.append(obs)
        logger.debug(f"[Telemetry Timing] {name}={duration_ms}ms tags={tags}")

    def get_observations(self) -> List[MetricObservation]:
        return list(self._observations)
