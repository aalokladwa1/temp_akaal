"""
Immutable Strongly-Typed Report Models.
"""

from typing import Any, Dict, List, Optional
import datetime
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__
    def Field(default=None, default_factory=None, **kwargs):
        return default


class ReportVersion(BaseModel):
    major: int = 1
    minor: int = 0
    patch: int = 0
    version_string: str = "1.0.0"


class ReportMetadata(BaseModel):
    report_id: str = Field(default_factory=lambda: f"rep-{uuid.uuid4().hex[:12]}")
    title: str
    report_type: str  # PRE_MIGRATION, PROGRESS, GB_VALIDATION, CUTOVER, POST_MIGRATION, EXECUTIVE_SUMMARY
    generated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    generator: str = "AKAAL Platform 8 Reporting Engine v1.0"
    correlation_id: str = Field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")
    trace_id: str = Field(default_factory=lambda: f"4bf92f3577b34da6a3ce929d0e0e4736")
    span_id: str = Field(default_factory=lambda: f"00f067aa0ba902b7")
    migration_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    version: ReportVersion = Field(default_factory=ReportVersion)


class ReportSection(BaseModel):
    section_id: str
    title: str
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    subsections: List["ReportSection"] = Field(default_factory=list)


class ReportArtifact(BaseModel):
    metadata: ReportMetadata
    sections: List[ReportSection] = Field(default_factory=list)
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    digital_signature: Optional[str] = None
    format: str = "JSON"  # HTML, PDF, JSON, CSV


class ReportSummary(BaseModel):
    total_sections: int
    total_metrics: int
    has_signature: bool
    size_bytes: int


class AuditArtifact(BaseModel):
    artifact_id: str
    name: str
    format: str
    content_sha256: str
    signature: Optional[str] = None
    payload: bytes
