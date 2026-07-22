"""
IPlatform8Facade Interface and Platform8Facade Implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from akaal.reporting.api.client import ReportingClient
from akaal.reporting.contracts.dto import AuditPackageDTO, ReportArtifactDTO, ReportRequestDTO


class IPlatform8Facade(ABC):
    """Abstract Interface for Platform 8 Enterprise Reporting Façade."""

    @abstractmethod
    async def generate_report(self, request: ReportRequestDTO) -> ReportArtifactDTO:
        pass

    @abstractmethod
    async def generate_audit_package(self, migration_id: str, report_types: List[str]) -> AuditPackageDTO:
        pass


class Platform8Facade(IPlatform8Facade):
    """Production Implementation of Platform 8 Façade."""

    def __init__(self, client: Optional[ReportingClient] = None) -> None:
        self.client = client or ReportingClient()

    async def generate_report(self, request: ReportRequestDTO) -> ReportArtifactDTO:
        return await self.client.generate_report(request)

    async def generate_audit_package(self, migration_id: str, report_types: List[str]) -> AuditPackageDTO:
        return await self.client.generate_audit_package(migration_id, report_types)
