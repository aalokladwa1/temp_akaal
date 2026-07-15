from dataclasses import dataclass
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.risk import RiskAssessment

@dataclass(frozen=True)
class SimulationReport:
    metadata: ReportMetadata
    estimated_time_ms: float
    estimated_storage_bytes: int
    estimated_cost: float
    risk: RiskAssessment
