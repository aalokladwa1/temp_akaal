"""
akaalEngine.telemetry.models.health
====================================
Canonical component health state models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Sequence


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ComponentHealth:
    """Component health snapshot."""
    component: str
    state: HealthState
    reason: str = "Operating normally"
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "state": self.state.value,
            "reason": self.reason,
            "observed_at": self.observed_at,
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class HealthSnapshot:
    """System-wide aggregate health snapshot."""
    overall_state: HealthState
    components: Sequence[ComponentHealth]
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_state": self.overall_state.value,
            "components": [c.to_dict() for c in self.components],
            "observed_at": self.observed_at,
        }
