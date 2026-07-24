"""
AKAAL Platform 9 — Reliability Intelligence Domain Models.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from akaal.reliability_intelligence.domain.enums import DriftSeverity, RegressionStatus


@dataclass(frozen=True)
class ReliabilityBaseline:
    baseline_id: str
    target_name: str
    p99_latency_ms: float
    error_rate_pct: float
    availability_pct: float
    created_at: str


@dataclass(frozen=True)
class DriftReport:
    report_id: str
    target_name: str
    drift_severity: DriftSeverity
    baseline_p99_ms: float
    current_p99_ms: float
    latency_delta_pct: float
    detected_at: str


@dataclass(frozen=True)
class RegressionReport:
    report_id: str
    target_name: str
    status: RegressionStatus
    regressions_found: List[str]
    evaluated_at: str


@dataclass(frozen=True)
class ReliabilityRecommendation:
    recommendation_id: str
    service_id: str
    title: str
    action_item: str
    priority: str
