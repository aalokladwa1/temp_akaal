"""
DTO Contracts for Platform 8 Reporting.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReportRequestDTO(BaseModel):
    report_type: str  # PRE_MIGRATION, PROGRESS, GB_VALIDATION, CUTOVER, POST_MIGRATION, EXECUTIVE_SUMMARY
    migration_id: str
    export_format: str = "JSON"  # HTML, PDF, JSON, CSV
    correlation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ReportArtifactDTO(BaseModel):
    report_id: str
    report_type: str
    format: str
    content_b64: str
    checksum_sha256: str
    generated_at: str
    signature: Optional[str] = None


class AuditPackageDTO(BaseModel):
    package_id: str
    migration_id: str
    reports_count: int
    manifest_sha256: str
    artifacts: List[ReportArtifactDTO] = Field(default_factory=list)
    package_signature: Optional[str] = None
    timestamp: str
