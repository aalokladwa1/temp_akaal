"""
Platform 8 Public Façade — Enterprise Reporting Integration.
"""

from typing import List, Optional
from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.facades.base import IFacade
from akaal.reporting.api.facade import Platform8Facade as ConcretePlatform8Facade, IPlatform8Facade
from akaal.reporting.contracts.dto import ReportRequestDTO


class Platform8Facade(IFacade, IPlatform8Facade):
    """Platform 7 Integration Wrapper for Platform 8 Reporting Engine."""

    def __init__(self, inner_facade: Optional[IPlatform8Facade] = None) -> None:
        self._inner = inner_facade or ConcretePlatform8Facade()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 8 (Reporting Engine)",
            version="1.0.0",
            supported_features=[
                "premigration_report",
                "progress_report",
                "gb_validation_report",
                "cutover_report",
                "postmigration_report",
                "executive_summary_report",
                "audit_package_builder",
                "report_versioning",
                "digital_signatures",
            ],
            active_protocols=["REST", "gRPC", "PDF", "HTML", "JSON", "CSV"],
        )

    async def generate_report(self, request: ReportRequestDTO):
        return await self._inner.generate_report(request)

    async def generate_audit_package(self, migration_id: str, report_types: List[str]):
        return await self._inner.generate_audit_package(migration_id, report_types)
