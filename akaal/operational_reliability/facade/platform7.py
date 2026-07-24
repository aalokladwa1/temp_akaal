"""
AKAAL Platform 7 — Enterprise Operational Reliability Platform Main Engine (EnterpriseOperationalReliabilityPlatformV7).
"""

from typing import Dict, Any, List, Optional

from akaal.operational_reliability.domain.models import (
    Incident,
    OperationalReadinessReport,
    ReliabilityAlert,
    ReliabilityScorecard,
    ServiceDescriptor,
    ServiceHealthNode,
    ServiceOwnership,
    SLOTarget,
)
from akaal.operational_reliability.domain.enums import (
    CriticalityLevel,
    HealthStatus,
    IncidentSeverity,
    ServiceTier,
)
from akaal.operational_reliability.service_catalog.registry import ServiceCatalogRegistry
from akaal.operational_reliability.service_catalog.ownership import ServiceOwnershipManager
from akaal.operational_reliability.maintenance.maintenance_manager import MaintenanceManager
from akaal.operational_reliability.slo.slo_service import SLOMonitoringService
from akaal.operational_reliability.sla.sla_service import SLAMonitoringService
from akaal.operational_reliability.error_budget.budget_manager import ErrorBudgetManager
from akaal.operational_reliability.analytics.mttr_engine import MTTRAnalyticsEngine
from akaal.operational_reliability.analytics.mtbf_engine import MTBFAnalyticsEngine
from akaal.operational_reliability.scorecards.generator import ReliabilityScorecardGenerator
from akaal.operational_reliability.readiness.readiness_engine import ReadinessAssessmentEngine
from akaal.operational_reliability.assessment.assessment_engine import ReliabilityAssessmentEngine
from akaal.operational_reliability.incidents.manager import IncidentManager
from akaal.operational_reliability.service_health.aggregator import ServiceHealthAggregator
from akaal.operational_reliability.dependency_health.monitor import DependencyHealthMonitor
from akaal.operational_reliability.alerting.router import AlertingEscalationEngine
from akaal.operational_reliability.runbooks.manager import RunbookManager
from akaal.operational_reliability.pir.pir_manager import PostIncidentReviewManager
from akaal.operational_reliability.forecasting.forecaster import ReliabilityForecaster
from akaal.operational_reliability.risk_register.register import OperationalRiskRegister


class EnterpriseOperationalReliabilityPlatformV7:
    """
    Centralized Enterprise Operational Reliability Platform (AKAAL Phase 12 Platform 7).
    Covers Service Catalog, Maintenance Windows, SLOs/SLAs, Error Budgets, MTTR/MTBF Analytics,
    Incidents, Health Aggregation, Alerts, Runbooks, PIRs, Readiness, and Operational Risks.
    """

    def __init__(self) -> None:
        self.platform_name = "Phase 12 Platform 7 — Enterprise Operational Reliability Platform"
        self.version = "7.0.0"
        self.profile = "ENTERPRISE"

        self.service_catalog = ServiceCatalogRegistry()
        self.ownership_manager = ServiceOwnershipManager()
        self.maintenance_manager = MaintenanceManager()
        self.slo_service = SLOMonitoringService()
        self.sla_service = SLAMonitoringService()
        self.error_budget_manager = ErrorBudgetManager()
        self.mttr_engine = MTTRAnalyticsEngine()
        self.mtbf_engine = MTBFAnalyticsEngine()
        self.scorecard_generator = ReliabilityScorecardGenerator()
        self.readiness_engine = ReadinessAssessmentEngine()
        self.assessment_engine = ReliabilityAssessmentEngine()
        self.incident_manager = IncidentManager()
        self.health_aggregator = ServiceHealthAggregator()
        self.dependency_monitor = DependencyHealthMonitor()
        self.alerting_engine = AlertingEscalationEngine()
        self.runbook_manager = RunbookManager()
        self.pir_manager = PostIncidentReviewManager()
        self.forecaster = ReliabilityForecaster()
        self.risk_register = OperationalRiskRegister()

        # Seed core AKAAL Platform default service descriptors
        self._seed_default_services()

    def _seed_default_services(self) -> None:
        core_services = [
            ("workflow-engine", "AKAAL Workflow Engine", ServiceTier.TIER_0, CriticalityLevel.CRITICAL),
            ("distributed-runtime", "AKAAL Distributed Runtime", ServiceTier.TIER_0, CriticalityLevel.CRITICAL),
            ("streaming-runtime", "AKAAL Streaming Runtime", ServiceTier.TIER_1, CriticalityLevel.HIGH),
            ("cdc-coordinator", "AKAAL CDC Coordinator", ServiceTier.TIER_1, CriticalityLevel.HIGH),
            ("schema-evolution", "AKAAL Schema Evolution", ServiceTier.TIER_1, CriticalityLevel.HIGH),
            ("governance-platform", "AKAAL Enterprise Governance", ServiceTier.TIER_0, CriticalityLevel.CRITICAL),
        ]
        for sid, name, tier, crit in core_services:
            own = ServiceOwnership(sid, "Enterprise Ops", "SRE Core", "sre-oncall@akaal.io", "sre@akaal.io")
            svc = ServiceDescriptor(sid, name, f"{name} Production Service", tier, crit, own, ["core", "p7-monitored"])
            self.service_catalog.register_service(svc)

    def report_health_telemetry(self, service_id: str, status: HealthStatus, latency_p99_ms: float, error_rate_pct: float) -> ServiceHealthNode:
        return self.health_aggregator.ingest_health(service_id, status, latency_p99_ms, error_rate_pct)

    def evaluate_readiness(self, target_system: str) -> OperationalReadinessReport:
        svc = self.service_catalog.get_service(target_system) if target_system in self.service_catalog._services else None
        health_ok = True
        if svc:
            health = self.health_aggregator.get_service_health(svc.service_id)
            if health and health.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                health_ok = False
        rb = self.runbook_manager.get_runbook_for_service(target_system) if svc else None
        return self.readiness_engine.evaluate_readiness(target_system, health_ok, rb is not None, True)
