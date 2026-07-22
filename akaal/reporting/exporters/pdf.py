"""
PDF Exporter Implementation.
"""

from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.templates.engine import TemplateEngine


class PDFExporter(IReportExporter):
    """Enterprise PDF Exporter Engine."""

    def __init__(self, template_engine: TemplateEngine = None) -> None:
        self.engine = template_engine or TemplateEngine()

    @property
    def format_name(self) -> str:
        return "PDF"

    def export(self, artifact: ReportArtifact) -> bytes:
        # Build PDF payload header + HTML body wrapper
        html_str = self.engine.render_html(artifact)
        pdf_payload = f"%PDF-1.7\n%AKAAL-ENTERPRISE-REPORT\n{html_str}".encode("utf-8")
        return pdf_payload
