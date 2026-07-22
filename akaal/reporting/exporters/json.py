"""
JSON Exporter Implementation with Streaming Support.
"""

from typing import Generator
import json
from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.templates.engine import TemplateEngine


class JSONExporter(IReportExporter):
    """JSON Exporter Engine supporting full export and chunked streaming."""

    def __init__(self, template_engine: TemplateEngine = None) -> None:
        self.engine = template_engine or TemplateEngine()

    @property
    def format_name(self) -> str:
        return "JSON"

    def export(self, artifact: ReportArtifact) -> bytes:
        json_str = self.engine.render_json(artifact)
        return json_str.encode("utf-8")

    def export_chunks(self, artifact: ReportArtifact, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        payload = self.export(artifact)
        for i in range(0, len(payload), chunk_size):
            yield payload[i : i + chunk_size]
