from dataclasses import dataclass
from typing import Tuple
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.risk import RiskAssessment

@dataclass(frozen=True)
class ValidationReport:
    metadata: ReportMetadata
    success: bool
    diagnostics: Tuple[ReliabilityDiagnostic, ...]
    risk: RiskAssessment
