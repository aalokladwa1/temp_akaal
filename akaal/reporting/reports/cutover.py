"""
Cutover Window & Readiness Report Generator.
"""

from typing import Dict, Any, Optional
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.models.report import ReportArtifact, ReportSection


class CutoverReport:
    """Cutover Window Report Generator."""

    def __init__(self, metadata_mgr: Optional[MetadataManager] = None) -> None:
        self.meta_mgr = metadata_mgr or MetadataManager()

    def generate(self, migration_id: str, cutover_data: Dict[str, Any]) -> ReportArtifact:
        meta = self.meta_mgr.create_metadata(
            title=f"Cutover Readiness & Execution Report - {migration_id}",
            report_type="CUTOVER",
            migration_id=migration_id,
        )

        sections = [
            ReportSection(
                section_id="sec-cut-1",
                title="Downtime & Rollback Readiness",
                content=f"Cutover window duration: {cutover_data.get('downtime_minutes', 12)} mins. Rollback readiness status: {cutover_data.get('rollback_ready', True)}.",
                structured_data=cutover_data,
            )
        ]

        return ReportArtifact(metadata=meta, sections=sections, summary_metrics={"switch_timestamp": cutover_data.get("switch_timestamp", "2026-07-22T02:00:00Z")})
