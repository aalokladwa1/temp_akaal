"""
AKAAL Platform 7 — Service Level Objective (SLO) Monitoring Service.
"""

from typing import Dict, List, Optional
from akaal.operational_reliability.domain.models import SLOTarget


class SLOMonitoringService:
    """Tracks Service Level Objectives (SLOs), availability, latency, and success rates."""

    def __init__(self) -> None:
        self._slos: Dict[str, SLOTarget] = {}
        self._current_metrics: Dict[str, float] = {}

    def register_slo(self, slo: SLOTarget) -> SLOTarget:
        self._slos[slo.slo_id] = slo
        self._current_metrics[slo.slo_id] = 100.0  # Default 100% attainment
        return slo

    def record_slo_measurement(self, slo_id: str, current_attainment: float) -> None:
        self._current_metrics[slo_id] = current_attainment

    def is_slo_compliant(self, slo_id: str) -> bool:
        slo = self._slos.get(slo_id)
        if not slo:
            return True
        actual = self._current_metrics.get(slo_id, 100.0)
        return actual >= slo.target_percentage
