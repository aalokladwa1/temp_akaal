"""
AKAAL Platform 9 — Reliability Baseline Comparator.
"""

from akaal.reliability_intelligence.domain.models import ReliabilityBaseline
import datetime
import uuid


class ReliabilityBaselineComparator:
    """Establishes and compares system performance against historical baselines."""

    def create_baseline(self, target_name: str, p99_latency_ms: float, error_rate_pct: float, availability_pct: float) -> ReliabilityBaseline:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return ReliabilityBaseline(
            baseline_id=f"bsl-{uuid.uuid4().hex[:8]}",
            target_name=target_name,
            p99_latency_ms=p99_latency_ms,
            error_rate_pct=error_rate_pct,
            availability_pct=availability_pct,
            created_at=now,
        )
