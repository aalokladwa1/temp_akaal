"""
AKAAL Platform 7 — Immutable Domain Models.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from akaal.operational_reliability.domain.enums import (
    CriticalityLevel,
    HealthStatus,
    IncidentSeverity,
    IncidentStatus,
    MaintenanceState,
    MaintenanceType,
    RiskSeverity,
    ServiceTier,
)


@dataclass(frozen=True)
class ServiceOwnership:
    service_id: str
    business_owner: str
    technical_owner: str
    on_call_team: str
    contact_email: str


@dataclass(frozen=True)
class ServiceDescriptor:
    service_id: str
    name: str
    description: str
    tier: ServiceTier
    criticality: CriticalityLevel
    ownership: ServiceOwnership
    tags: List[str]
    linked_slo_ids: List[str] = field(default_factory=list)
    linked_runbook_ids: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass(frozen=True)
class MaintenanceWindow:
    window_id: str
    service_id: str
    title: str
    maintenance_type: MaintenanceType
    state: MaintenanceState
    start_time: str
    end_time: str
    suppress_alerts: bool = True
    approved_by: str = "change_advisory_board"


@dataclass(frozen=True)
class SLOTarget:
    slo_id: str
    name: str
    service_id: str
    target_percentage: float
    time_window_days: int
    metric_type: str


@dataclass(frozen=True)
class ErrorBudget:
    slo_id: str
    total_budget_minutes: float
    remaining_budget_minutes: float
    consumed_percentage: float
    burn_rate_1h: float
    burn_rate_24h: float
    is_exhausted: bool


@dataclass(frozen=True)
class MTTRMetric:
    service_id: str
    mean_time_to_recovery_minutes: float
    total_incidents_measured: int
    measured_at: str


@dataclass(frozen=True)
class MTBFMetric:
    service_id: str
    mean_time_between_failures_hours: float
    total_failures: int
    measured_at: str


@dataclass(frozen=True)
class Incident:
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    impacted_services: List[str]
    opened_at: str
    resolved_at: Optional[str]
    root_cause_summary: Optional[str]
    lead_sre_id: str


@dataclass(frozen=True)
class PostIncidentReview:
    pir_id: str
    incident_id: str
    root_cause_analysis: str
    contributing_factors: List[str]
    corrective_actions: List[str]
    preventive_actions: List[str]
    lessons_learned: List[str]
    completed_at: str


@dataclass(frozen=True)
class ServiceHealthNode:
    service_id: str
    status: HealthStatus
    latency_p99_ms: float
    error_rate_pct: float
    updated_at: str


@dataclass(frozen=True)
class DependencyHealthNode:
    source_service_id: str
    target_service_id: str
    status: HealthStatus
    cascade_risk_score: float


@dataclass(frozen=True)
class ReliabilityAlert:
    alert_id: str
    service_id: str
    summary: str
    severity: IncidentSeverity
    triggered_at: str
    is_suppressed: bool = False


@dataclass(frozen=True)
class OperationalRunbook:
    runbook_id: str
    title: str
    service_id: str
    trigger_conditions: List[str]
    steps: List[str]
    author: str


@dataclass(frozen=True)
class OperationalReadinessReport:
    report_id: str
    target_system: str
    overall_readiness_score: float
    is_deployment_ready: bool
    risk_posture: str
    blockers: List[str]
    assessed_at: str


@dataclass(frozen=True)
class ReliabilityScorecard:
    scorecard_id: str
    target_name: str
    reliability_score: float
    slo_attainment_pct: float
    mttr_compliance_pct: float
    generated_at: str


@dataclass(frozen=True)
class OperationalRisk:
    risk_id: str
    service_id: str
    title: str
    severity: RiskSeverity
    mitigation_plan: str
    residual_risk_score: float


@dataclass(frozen=True)
class ReliabilityForecast:
    forecast_id: str
    service_id: str
    predicted_availability_30d: float
    error_budget_exhaustion_days: float
    capacity_risk_level: str
    generated_at: str
