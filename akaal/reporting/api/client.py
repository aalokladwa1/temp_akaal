"""
ReportingClient Public Client Facade for Platform 8.
"""

from typing import List, Optional
from akaal.reporting.contracts.dto import AuditPackageDTO, ReportArtifactDTO, ReportRequestDTO
from akaal.reporting.engine.engine import ReportEngine


class ReportingClient:
    """Public Client Facade providing API access to Platform 8 Enterprise Reporting."""

    def __init__(self, engine: Optional[ReportEngine] = None) -> None:
        self.engine = engine or ReportEngine()

    async def generate_report(self, request: ReportRequestDTO) -> ReportArtifactDTO:
        """Generate enterprise report matching specified type and export format."""
        return self.engine.generate_report(request)

    async def generate_audit_package(self, migration_id: str, report_types: List[str]) -> AuditPackageDTO:
        """Generate cryptographically signed multi-report enterprise audit package."""
        return self.engine.generate_audit_package(migration_id, report_types)
