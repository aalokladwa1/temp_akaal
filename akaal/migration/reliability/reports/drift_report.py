from dataclasses import dataclass
from typing import Tuple
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.risk import RiskAssessment

@dataclass(frozen=True)
class DriftReport:
    metadata: ReportMetadata
    has_drift: bool
    drifts: Tuple[str, ...]
    risk: RiskAssessment
