"""
Abstract Report Exporter Interface.
"""

from abc import ABC, abstractmethod
from akaal.reporting.models.report import ReportArtifact


class IReportExporter(ABC):
    """Abstract Interface for Exporters converting ReportArtifact to output formats."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        pass

    @abstractmethod
    def export(self, artifact: ReportArtifact) -> bytes:
        """Export report artifact to raw byte payload."""
        pass
