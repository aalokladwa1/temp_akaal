"""
CSV Exporter Implementation with Streaming Support.
"""

from typing import Generator
from akaal.reporting.exporters.base import IReportExporter
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.templates.engine import TemplateEngine


class CSVExporter(IReportExporter):
    """CSV Exporter Engine supporting full export and chunked streaming."""

    def __init__(self, template_engine: TemplateEngine = None) -> None:
        self.engine = template_engine or TemplateEngine()

    @property
    def format_name(self) -> str:
        return "CSV"

    def export(self, artifact: ReportArtifact) -> bytes:
        csv_str = self.engine.render_csv(artifact)
        return csv_str.encode("utf-8")

    def export_chunks(self, artifact: ReportArtifact, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        # Header chunk
        yield b"Section,Title,Content\n"
        for s in artifact.sections:
            safe_content = s.content.replace('"', '""')
            line = f'"{s.section_id}","{s.title}","{safe_content}"\n'
            yield line.encode("utf-8")
