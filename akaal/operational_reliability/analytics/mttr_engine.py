"""
AKAAL Platform 7 — MTTR (Mean Time To Recovery) Analytics Engine.
"""

from typing import List
import datetime
from akaal.operational_reliability.domain.models import MTTRMetric


class MTTRAnalyticsEngine:
    """Calculates Mean Time To Recovery (MTTR) trends and benchmarks."""

    def compute_mttr(self, service_id: str, recovery_durations_minutes: List[float]) -> MTTRMetric:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not recovery_durations_minutes:
            return MTTRMetric(service_id=service_id, mean_time_to_recovery_minutes=0.0, total_incidents_measured=0, measured_at=now)

        mean_mttr = sum(recovery_durations_minutes) / len(recovery_durations_minutes)
        return MTTRMetric(
            service_id=service_id,
            mean_time_to_recovery_minutes=round(mean_mttr, 2),
            total_incidents_measured=len(recovery_durations_minutes),
            measured_at=now,
        )
