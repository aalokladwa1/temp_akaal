from dataclasses import dataclass

@dataclass(frozen=True)
class ReportMetadata:
    engine_version: str
    schema_version: str
    generated_at: float
    execution_id: str
    report_id: str
