"""
Executive Summary Business Report Generator.
"""

from typing import Dict, Any, Optional
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.models.report import ReportArtifact, ReportSection


class ExecutiveSummaryReport:
    """Executive Summary Business Report Generator."""

    def __init__(self, metadata_mgr: Optional[MetadataManager] = None) -> None:
        self.meta_mgr = metadata_mgr or MetadataManager()

    def generate(self, migration_id: str, exec_data: Dict[str, Any]) -> ReportArtifact:
        meta = self.meta_mgr.create_metadata(
            title=f"Executive Migration Summary & SLA Brief - {migration_id}",
            report_type="EXECUTIVE_SUMMARY",
            migration_id=migration_id,
        )

        sections = [
            ReportSection(
                section_id="sec-exec-1",
                title="Project Overview & SLA Compliance",
                content=f"Overall project migration completed with {exec_data.get('success_rate', '99.99%')} success rate under SLA target of {exec_data.get('sla_target', '99.9%')}.",
                structured_data=exec_data,
            )
        ]

        return ReportArtifact(metadata=meta, sections=sections, summary_metrics={"overall_status": "SUCCESS", "sla_met": True})
