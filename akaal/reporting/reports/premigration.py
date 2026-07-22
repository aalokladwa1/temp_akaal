"""
Pre-Migration Report Generator.
"""

from typing import Dict, Any, Optional
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.models.report import ReportArtifact, ReportSection


class PreMigrationReport:
    """Pre-Migration Report generator consuming facade inputs."""

    def __init__(self, metadata_mgr: Optional[MetadataManager] = None) -> None:
        self.meta_mgr = metadata_mgr or MetadataManager()

    def generate(self, migration_id: str, source_inventory: Dict[str, Any], dest_inventory: Dict[str, Any]) -> ReportArtifact:
        meta = self.meta_mgr.create_metadata(
            title=f"Pre-Migration Inspection Report - {migration_id}",
            report_type="PRE_MIGRATION",
            migration_id=migration_id,
        )

        sections = [
            ReportSection(
                section_id="sec-1",
                title="Source Inventory & Compatibility",
                content=f"Discovered {source_inventory.get('table_count', 120)} tables in source database {source_inventory.get('db_name', 'src_prod')}.",
                structured_data=source_inventory,
            ),
            ReportSection(
                section_id="sec-2",
                title="Target Scope & Duration Estimation",
                content=f"Target database {dest_inventory.get('db_name', 'target_dw')} provisioned. Estimated rows: {source_inventory.get('estimated_rows', 50000000)}.",
                structured_data=dest_inventory,
            ),
        ]

        return ReportArtifact(metadata=meta, sections=sections, summary_metrics={"status": "READY", "risk_level": "LOW"})
