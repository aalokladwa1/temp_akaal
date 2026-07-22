"""
Abstract Report Exporter Interface with Streaming & Spill-to-Disk Support.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Generator
import tempfile
import os
from akaal.reporting.models.report import ReportArtifact


class SpillToDiskManager:
    """Spill-to-disk manager for large multi-GB report payloads."""

    def __init__(self, memory_threshold_mb: float = 50.0) -> None:
        self.threshold_bytes = int(memory_threshold_mb * 1024 * 1024)

    def write_spill_file(self, chunks: Generator[bytes, None, None]) -> str:
        fd, path = tempfile.mkstemp(prefix="akaal_rep_spill_", suffix=".tmp")
        total = 0
        with os.fdopen(fd, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
                total += len(chunk)
        return path


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

    def export_chunks(self, artifact: ReportArtifact, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        """Stream report artifact in chunks for large payloads."""
        payload = self.export(artifact)
        for i in range(0, len(payload), chunk_size):
            yield payload[i : i + chunk_size]
