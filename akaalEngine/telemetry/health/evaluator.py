"""
akaalEngine.telemetry.health.evaluator
=======================================
HealthEvaluator aggregating component health snapshots into system-wide HealthSnapshot.
Mined from `akaal/performance/health/score.py`.
"""

import logging
from threading import RLock
from typing import Dict, List, Optional

from akaalEngine.telemetry.models.health import ComponentHealth, HealthSnapshot, HealthState

logger = logging.getLogger("akaalEngine.telemetry.health.evaluator")


class HealthEvaluator:
    """
    Thread-safe component health evaluator.
    Computes overall system health from individual component health statuses.
    """

    def __init__(self) -> None:
        self._components: Dict[str, ComponentHealth] = {}
        self._lock = RLock()

    def update_component_health(
        self,
        component: str,
        state: HealthState,
        reason: str = "Operating normally",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ComponentHealth:
        with self._lock:
            comp_health = ComponentHealth(
                component=component,
                state=state,
                reason=reason,
                metrics=dict(metrics or {}),
            )
            self._components[component] = comp_health
            return comp_health

    def get_snapshot(self) -> HealthSnapshot:
        with self._lock:
            comps = list(self._components.values())

            # Evaluate aggregate overall state: UNHEALTHY > DEGRADED > UNKNOWN > HEALTHY
            if any(c.state == HealthState.UNHEALTHY for c in comps):
                overall = HealthState.UNHEALTHY
            elif any(c.state == HealthState.DEGRADED for c in comps):
                overall = HealthState.DEGRADED
            elif any(c.state == HealthState.UNKNOWN for c in comps):
                overall = HealthState.UNKNOWN
            else:
                overall = HealthState.HEALTHY

            return HealthSnapshot(
                overall_state=overall,
                components=comps,
            )
