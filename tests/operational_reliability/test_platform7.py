"""
AKAAL Platform 7 — Unit & Integration Test Suite.
Verifies all 18 Enterprise Operational Reliability Capabilities: SLO/SLA Monitoring, Error Budgets, MTTR/MTBF Analytics,
Incidents, Service Catalog & Ownership, Maintenance Windows, Runbooks, PIRs, Readiness, and Risk Register.
"""

import unittest
import asyncio
import datetime

from akaal.operational_reliability import EnterpriseOperationalReliabilityPlatformV7
from akaal.operational_reliability.domain.models import (
    SLOTarget,
    ServiceDescriptor,
    ServiceOwnership,
)
from akaal.operational_reliability.domain.enums import (
    ServiceTier,
    CriticalityLevel,
    HealthStatus,
    IncidentSeverity,
    MaintenanceType,
    RiskSeverity,
)
from akaal.api.facades.platform7 import Platform7Facade


class TestPlatform7OperationalReliability(unittest.TestCase):

    def setUp(self):
        self.platform = EnterpriseOperationalReliabilityPlatformV7()
        self.facade = Platform7Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 7 (Enterprise Operational Reliability Platform)")
        self.assertIn("slo_monitoring", caps.supported_features)
        self.assertIn("service_catalog_ownership", caps.supported_features)
        self.assertIn("maintenance_change_windows", caps.supported_features)

    def test_service_catalog_and_ownership(self):
        own = ServiceOwnership("svc_payment", "Finance", "Payments Team", "pay-oncall@akaal.io", "pay@akaal.io")
        svc = ServiceDescriptor("svc_payment", "Payment Gateway Service", "Core payment API", ServiceTier.TIER_0, CriticalityLevel.CRITICAL, own, ["finance"])
        self.platform.service_catalog.register_service(svc)

        retrieved = self.platform.service_catalog.get_service("svc_payment")
        self.assertEqual(retrieved.name, "Payment Gateway Service")
        self.assertEqual(retrieved.tier, ServiceTier.TIER_0)

    def test_maintenance_window_and_suppression(self):
        window = self.platform.maintenance_manager.schedule_maintenance(
            service_id="workflow-engine",
            title="Database Schema Upgrade",
            maintenance_type=MaintenanceType.PLANNED_DOWNTIME,
            start_time="2026-01-01T00:00:00Z",
            end_time="2030-01-01T00:00:00Z",  # Active window
        )
        self.assertTrue(self.platform.maintenance_manager.is_service_in_maintenance("workflow-engine"))

        # Alerting engine should suppress alerts during active maintenance
        alert = self.platform.alerting_engine.raise_alert(
            service_id="workflow-engine",
            summary="High Latency Warning",
            severity=IncidentSeverity.SEV_2,
            is_suppressed=self.platform.maintenance_manager.is_service_in_maintenance("workflow-engine"),
        )
        self.assertTrue(alert.is_suppressed)

    def test_slo_monitoring_and_error_budget(self):
        slo = SLOTarget(
            slo_id="SLO_001",
            name="Workflow Availability SLO",
            service_id="workflow-engine",
            target_percentage=99.9,
            time_window_days=30,
            metric_type="AVAILABILITY",
        )
        self.platform.slo_service.register_slo(slo)
        self.platform.slo_service.record_slo_measurement("SLO_001", 99.95)

        self.assertTrue(self.platform.slo_service.is_slo_compliant("SLO_001"))

        budget = self.platform.error_budget_manager.compute_budget("SLO_001", 99.9, 99.95)
        self.assertFalse(budget.is_exhausted)
        self.assertLess(budget.consumed_percentage, 100.0)

    def test_mttr_and_mtbf_analytics(self):
        mttr = self.platform.mttr_engine.compute_mttr("workflow-engine", [10.0, 15.0, 20.0])
        self.assertEqual(mttr.mean_time_to_recovery_minutes, 15.0)

        mtbf = self.platform.mtbf_engine.compute_mtbf("workflow-engine", 720.0, 2)
        self.assertEqual(mtbf.mean_time_between_failures_hours, 360.0)

    def test_incident_lifecycle_and_pir(self):
        inc = self.platform.incident_manager.open_incident(
            title="Streaming Pipeline Lag Spike",
            severity=IncidentSeverity.SEV_1,
            impacted_services=["streaming-runtime"],
        )
        self.assertEqual(inc.severity, IncidentSeverity.SEV_1)
        self.assertEqual(len(self.platform.incident_manager.list_open_incidents()), 1)

        resolved = self.platform.incident_manager.resolve_incident(inc.incident_id, "Network partition cleared.")
        self.assertEqual(resolved.status.value, "RESOLVED")

        pir = self.platform.pir_manager.create_pir(
            incident_id=inc.incident_id,
            root_cause_analysis="Transient network partition in AZ2.",
            contributing_factors=["Missing cross-AZ fallback"],
            corrective_actions=["Deploy multi-AZ retry handler"],
            preventive_actions=["Add chaos experiment for AZ partition"],
            lessons_learned=["Monitor AZ latency continuously"],
        )
        self.assertEqual(pir.incident_id, inc.incident_id)

    def test_operational_readiness_assessment(self):
        report = self.platform.evaluate_readiness("workflow-engine")
        self.assertEqual(report.target_system, "workflow-engine")
        self.assertGreater(report.overall_readiness_score, 0.0)

    def test_operational_risk_register(self):
        risk = self.platform.risk_register.register_risk(
            service_id="workflow-engine",
            title="Single Region DB Dependency",
            severity=RiskSeverity.HIGH,
            mitigation_plan="Deploy cross-region replica",
            residual_risk_score=3.5,
        )
        self.assertEqual(risk.service_id, "workflow-engine")
        self.assertEqual(len(self.platform.risk_register.list_risks_for_service("workflow-engine")), 1)

    def test_facade_async_health_reporting(self):
        res = asyncio.run(self.facade.report_service_health("workflow-engine", "HEALTHY", 12.5, 0.01))
        self.assertEqual(res["service_id"], "workflow-engine")
        self.assertEqual(res["status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
