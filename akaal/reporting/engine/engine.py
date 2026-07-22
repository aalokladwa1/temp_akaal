"""
Enterprise Report Engine Coordinator.
"""

from typing import Dict, List, Optional
from akaal.reporting.audit.builder import AuditPackageBuilder
from akaal.reporting.contracts.dto import AuditPackageDTO, ReportArtifactDTO, ReportRequestDTO
from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.exporters.csv import CSVExporter
from akaal.reporting.exporters.html import HTMLExporter
from akaal.reporting.exporters.json import JSONExporter
from akaal.reporting.exporters.pdf import PDFExporter
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.reports.cutover import CutoverReport
from akaal.reporting.reports.executive import ExecutiveSummaryReport
from akaal.reporting.reports.postmigration import PostMigrationReport
from akaal.reporting.reports.premigration import PreMigrationReport
from akaal.reporting.reports.progress import MigrationProgressReport
from akaal.reporting.reports.validation import GBValidationReport
from akaal.reporting.signing.base import ISigningProvider
from akaal.reporting.signing.x509 import X509SigningProvider
from akaal.reporting.versioning.manager import ReportVersionManager


class ReportEngine:
    """Master Enterprise Report Engine Coordinator."""

    def __init__(
        self,
        signing_provider: Optional[ISigningProvider] = None,
        version_manager: Optional[ReportVersionManager] = None,
    ) -> None:
        self.meta_mgr = MetadataManager()
        self.version_mgr = version_manager or ReportVersionManager()
        self.signer = signing_provider or X509SigningProvider()
        self.audit_builder = AuditPackageBuilder(signing_provider=self.signer)

        self.exporters: Dict[str, IReportExporter] = {
            "HTML": HTMLExporter(),
            "JSON": JSONExporter(),
            "CSV": CSVExporter(),
            "PDF": PDFExporter(),
        }

        self.premigration_gen = PreMigrationReport(metadata_mgr=self.meta_mgr)
        self.progress_gen = MigrationProgressReport(metadata_mgr=self.meta_mgr)
        self.validation_gen = GBValidationReport(metadata_mgr=self.meta_mgr)
        self.cutover_gen = CutoverReport(metadata_mgr=self.meta_mgr)
        self.postmigration_gen = PostMigrationReport(metadata_mgr=self.meta_mgr)
        self.executive_gen = ExecutiveSummaryReport(metadata_mgr=self.meta_mgr)

    def generate_report(self, request: ReportRequestDTO) -> ReportArtifactDTO:
        report_type = request.report_type.upper()
        params = request.parameters

        if report_type == "PRE_MIGRATION":
            art = self.premigration_gen.generate(request.migration_id, params.get("source_inventory", {}), params.get("dest_inventory", {}))
        elif report_type == "PROGRESS":
            art = self.progress_gen.generate(request.migration_id, params.get("progress_data", {}))
        elif report_type == "GB_VALIDATION":
            art = self.validation_gen.generate(request.migration_id, params.get("validation_data", {}))
        elif report_type == "CUTOVER":
            art = self.cutover_gen.generate(request.migration_id, params.get("cutover_data", {}))
        elif report_type == "POST_MIGRATION":
            art = self.postmigration_gen.generate(request.migration_id, params.get("summary_data", {}))
        elif report_type == "EXECUTIVE_SUMMARY":
            art = self.executive_gen.generate(request.migration_id, params.get("exec_data", {}))
        else:
            raise ValueError(f"Unsupported report type: {request.report_type}")

        # Register semantic versioning
        self.version_mgr.register_version(art)

        # Export binary payload
        exporter = self.exporters.get(request.export_format.upper(), self.exporters["JSON"])
        payload = exporter.export(art)
        checksum = self.meta_mgr.compute_checksum(payload)
        sig = self.signer.sign_payload(payload)

        art.digital_signature = sig
        art.format = exporter.format_name

        import base64
        return ReportArtifactDTO(
            report_id=art.metadata.report_id,
            report_type=art.metadata.report_type,
            format=exporter.format_name,
            content_b64=base64.b64encode(payload).decode("utf-8"),
            checksum_sha256=checksum,
            generated_at=art.metadata.generated_at,
            signature=sig,
        )

    def generate_audit_package(self, migration_id: str, report_types: List[str]) -> AuditPackageDTO:
        artifacts = []
        payloads = []

        for rt in report_types:
            req = ReportRequestDTO(report_type=rt, migration_id=migration_id, export_format="JSON")
            dto = self.generate_report(req)
            import base64
            p = base64.b64decode(dto.content_b64.encode("utf-8"))
            art = self.premigration_gen.generate(migration_id, {}, {})
            art.metadata.report_id = dto.report_id
            art.metadata.report_type = dto.report_type
            artifacts.append(art)
            payloads.append(p)

        return self.audit_builder.build_package(migration_id, artifacts, payloads)
