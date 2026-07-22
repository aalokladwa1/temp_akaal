"""
Gigabyte/Gigacell Validation Report Generator.
"""

from typing import Dict, Any, Optional
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.models.report import ReportArtifact, ReportSection


class GBValidationReport:
    """GB Validation Report Generator."""

    def __init__(self, metadata_mgr: Optional[MetadataManager] = None) -> None:
        self.meta_mgr = metadata_mgr or MetadataManager()

    def generate(self, migration_id: str, validation_data: Dict[str, Any]) -> ReportArtifact:
        meta = self.meta_mgr.create_metadata(
            title=f"GB Validation Audit Report - {migration_id}",
            report_type="GB_VALIDATION",
            migration_id=migration_id,
        )

        sections = [
            ReportSection(
                section_id="sec-val-1",
                title="Checksum & Row Count Verification",
                content=f"Checksum verification status: {validation_data.get('status', 'PASSED')}. Mismatches detected: {validation_data.get('mismatches', 0)}.",
                structured_data=validation_data,
            )
        ]

        return ReportArtifact(metadata=meta, sections=sections, summary_metrics={"verification_status": validation_data.get("status", "PASSED")})
