"""
AKAAL Platform 7 — Enterprise Service Catalog Registry.
"""

from typing import Dict, List, Optional
from akaal.operational_reliability.domain.models import ServiceDescriptor
from akaal.operational_reliability.domain.enums import ServiceTier, CriticalityLevel
from akaal.operational_reliability.domain.exceptions import ServiceNotFoundError


class ServiceCatalogRegistry:
    """Centralized Operational Service Catalog maintaining service identity and metadata across AKAAL."""

    def __init__(self) -> None:
        self._services: Dict[str, ServiceDescriptor] = {}

    def register_service(self, service: ServiceDescriptor) -> ServiceDescriptor:
        self._services[service.service_id] = service
        return service

    def get_service(self, service_id: str) -> ServiceDescriptor:
        svc = self._services.get(service_id)
        if not svc:
            raise ServiceNotFoundError(f"Service '{service_id}' not found in Operational Service Catalog.")
        return svc

    def list_services(self, tier: Optional[ServiceTier] = None, criticality: Optional[CriticalityLevel] = None) -> List[ServiceDescriptor]:
        result = list(self._services.values())
        if tier:
            result = [s for s in result if s.tier == tier]
        if criticality:
            result = [s for s in result if s.criticality == criticality]
        return result
