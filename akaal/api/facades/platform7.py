"""
Platform 7 Public Façade — Operational Reliability Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime

from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.operational_reliability.facade.platform7 import EnterpriseOperationalReliabilityPlatformV7
from akaal.operational_reliability.domain.enums import HealthStatus, IncidentSeverity


class IPlatform7Facade(IFacade, ABC):
    """Abstract Interface for Platform 7 Operational Reliability Façade."""

    @abstractmethod
    async def report_service_health(self, service_id: str, status: str, latency_p99_ms: float, error_rate_pct: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_slo_status(self, slo_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def trigger_incident(self, title: str, severity: str, impacted_services: List[str]) -> Dict[str, Any]:
        pass


class Platform7Facade(IPlatform7Facade):
    """Production Platform 7 Façade Implementation routing to EnterpriseOperationalReliabilityPlatformV7."""

    def __init__(self, platform_engine: Optional[EnterpriseOperationalReliabilityPlatformV7] = None) -> None:
        self._engine = platform_engine or EnterpriseOperationalReliabilityPlatformV7()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 7 (Enterprise Operational Reliability Platform)",
            version="7.0.0",
            supported_features=[
                "slo_monitoring",
                "sla_monitoring",
                "error_budget_manager",
                "mttr_mtbf_analytics",
                "incident_management",
                "service_catalog_ownership",
                "maintenance_change_windows",
                "readiness_assessments",
                "operational_risk_register",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def report_service_health(self, service_id: str, status: str, latency_p99_ms: float, error_rate_pct: float) -> Dict[str, Any]:
        try:
            enum_status = HealthStatus(status.upper()) if hasattr(HealthStatus, status.upper()) else HealthStatus.HEALTHY
            node = self._engine.report_health_telemetry(service_id, enum_status, latency_p99_ms, error_rate_pct)
            return {
                "service_id": node.service_id,
                "status": node.status.value,
                "latency_p99_ms": node.latency_p99_ms,
                "error_rate_pct": node.error_rate_pct,
                "updated_at": node.updated_at,
            }
        except Exception as e:
            raise FacadeError(f"Failed to report service health on Platform 7: {str(e)}")

    async def get_slo_status(self, slo_id: str) -> Dict[str, Any]:
        try:
            slo = self._engine.slo_service._slos.get(slo_id)
            if not slo:
                return {"slo_id": slo_id, "status": "NOT_FOUND"}
            is_ok = self._engine.slo_service.is_slo_compliant(slo_id)
            actual = self._engine.slo_service._current_metrics.get(slo_id, 100.0)
            budget = self._engine.error_budget_manager.compute_budget(slo_id, slo.target_percentage, actual)
            return {
                "slo_id": slo_id,
                "name": slo.name,
                "target_percentage": slo.target_percentage,
                "current_percentage": actual,
                "is_compliant": is_ok,
                "remaining_budget_pct": 100.0 - budget.consumed_percentage,
            }
        except Exception as e:
            raise FacadeError(f"Failed to fetch SLO status on Platform 7: {str(e)}")

    async def trigger_incident(self, title: str, severity: str, impacted_services: List[str]) -> Dict[str, Any]:
        try:
            sev_enum = IncidentSeverity(severity.upper()) if hasattr(IncidentSeverity, severity.upper()) else IncidentSeverity.SEV_2
            inc = self._engine.incident_manager.open_incident(title, sev_enum, impacted_services)
            return {
                "incident_id": inc.incident_id,
                "title": inc.title,
                "severity": inc.severity.value,
                "status": inc.status.value,
                "opened_at": inc.opened_at,
            }
        except Exception as e:
            raise FacadeError(f"Failed to trigger incident on Platform 7: {str(e)}")
