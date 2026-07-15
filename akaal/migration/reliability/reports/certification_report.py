from dataclasses import dataclass
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.risk import RiskAssessment

@dataclass(frozen=True)
class MigrationCertificationReport:
    metadata: ReportMetadata
    certified: bool
    compliance_grade: str
    risk: RiskAssessment
