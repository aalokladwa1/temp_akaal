"""
AKAAL Platform 9 — Reliability Drift Detector.
"""

import datetime
import uuid
from akaal.reliability_intelligence.domain.models import DriftReport
from akaal.reliability_intelligence.domain.enums import DriftSeverity


class ReliabilityDriftDetector:
    """Detects gradual performance or reliability drift over time."""

    def detect_drift(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> DriftReport:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        delta_pct = round(((current_p99_ms - baseline_p99_ms) / max(0.001, baseline_p99_ms)) * 100.0, 2)

        if delta_pct > 50.0:
            severity = DriftSeverity.SEVERE
        elif delta_pct > 20.0:
            severity = DriftSeverity.MODERATE
        elif delta_pct > 5.0:
            severity = DriftSeverity.MINOR
        else:
            severity = DriftSeverity.NONE

        return DriftReport(
            report_id=f"drf-{uuid.uuid4().hex[:8]}",
            target_name=target_name,
            drift_severity=severity,
            baseline_p99_ms=baseline_p99_ms,
            current_p99_ms=current_p99_ms,
            latency_delta_pct=delta_pct,
            detected_at=now,
        )
