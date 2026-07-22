"""
DTO Contracts for Platform 8 Reporting.
"""

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in self.__class__.__dict__.items():
                if not k.startswith('_'):
                    if callable(v):
                        setattr(self, k, v())
                    elif v is not None:
                        setattr(self, k, v)
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.model_dump()
        def model_dump(self):
            res = {}
            for k, v in self.__dict__.items():
                if hasattr(v, "model_dump"):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if hasattr(item, "model_dump") else item for item in v]
                elif isinstance(v, dict):
                    res[k] = {dk: (dv.model_dump() if hasattr(dv, "model_dump") else dv) for dk, dv in v.items()}
                else:
                    res[k] = v
            return res
    def Field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory
        return default


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
