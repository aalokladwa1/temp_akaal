"""
AKAAL Platform 7 — MTBF (Mean Time Between Failures) Analytics Engine.
"""

from typing import List
import datetime
from akaal.operational_reliability.domain.models import MTBFMetric


class MTBFAnalyticsEngine:
    """Calculates Mean Time Between Failures (MTBF) and failure frequency trends."""

    def compute_mtbf(self, service_id: str, total_operational_hours: float, failure_count: int) -> MTBFMetric:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if failure_count == 0:
            mtbf = total_operational_hours
        else:
            mtbf = total_operational_hours / failure_count

        return MTBFMetric(
            service_id=service_id,
            mean_time_between_failures_hours=round(mtbf, 2),
            total_failures=failure_count,
            measured_at=now,
        )
