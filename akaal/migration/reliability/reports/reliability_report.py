from dataclasses import dataclass
from typing import Tuple, Optional
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.risk import RiskAssessment
from akaal.migration.reliability.reports.validation_report import ValidationReport
from akaal.migration.reliability.reports.health_report import HealthCheckReport
from akaal.migration.reliability.reports.certification_report import MigrationCertificationReport
from akaal.migration.reliability.reports.drift_report import DriftReport
from akaal.migration.reliability.reports.simulation_report import SimulationReport
from akaal.migration.reliability.reports.rollback_report import RollbackPlan

@dataclass(frozen=True)
class ReliabilityReport:
    metadata: ReportMetadata
    overall_risk: RiskAssessment
    validation: Optional[ValidationReport] = None
    health: Optional[HealthCheckReport] = None
    simulation: Optional[SimulationReport] = None
    certification: Optional[MigrationCertificationReport] = None
    rollback: Optional[RollbackPlan] = None
    drift: Optional[DriftReport] = None
    diagnostics: Tuple[ReliabilityDiagnostic, ...] = ()
