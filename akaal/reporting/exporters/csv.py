"""
CSV Exporter Implementation.
"""

from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.templates.engine import TemplateEngine


class CSVExporter(IReportExporter):
    """CSV Exporter Engine."""

    def __init__(self, template_engine: TemplateEngine = None) -> None:
        self.engine = template_engine or TemplateEngine()

    @property
    def format_name(self) -> str:
        return "CSV"

    def export(self, artifact: ReportArtifact) -> bytes:
        csv_str = self.engine.render_csv(artifact)
        return csv_str.encode("utf-8")
