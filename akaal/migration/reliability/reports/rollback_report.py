from dataclasses import dataclass
from typing import Tuple
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.risk import RiskAssessment

@dataclass(frozen=True)
class RollbackPlan:
    metadata: ReportMetadata
    steps: Tuple[str, ...]
    safe_to_rollback: bool
    risk: RiskAssessment
