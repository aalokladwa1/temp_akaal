"""
HTML Exporter Implementation.
"""

from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.templates.engine import TemplateEngine


class HTMLExporter(IReportExporter):
    """HTML Exporter Engine."""

    def __init__(self, template_engine: TemplateEngine = None) -> None:
        self.engine = template_engine or TemplateEngine()

    @property
    def format_name(self) -> str:
        return "HTML"

    def export(self, artifact: ReportArtifact) -> bytes:
        html_str = self.engine.render_html(artifact)
        return html_str.encode("utf-8")
