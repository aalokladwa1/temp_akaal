import time
from typing import List, Optional
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.reliability_report import ReliabilityReport
from akaal.migration.reliability.validation.engine import ValidationEngine
from akaal.migration.reliability.health.precheck_engine import HealthPrecheckEngine
from akaal.migration.reliability.simulation.dryrun_engine import DryRunSimulationEngine
from akaal.migration.reliability.certification.certification_engine import CertificationEngine
from akaal.migration.reliability.rollback.rollback_engine import RollbackEngine
from akaal.migration.reliability.drift.drift_detector import DriftDetector
from akaal.migration.reliability.utilities.hooks import (
    before_validation, after_validation,
    before_health_check, after_health_check,
    before_simulation, after_simulation,
    before_certification, after_certification,
    before_rollback_generation, after_rollback_generation
)
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment

class ReliabilityPipeline:
    """Orchestrator to configure, run, and aggregate validation and precheck workflows."""
    def __init__(self, enabled_steps: Optional[List[str]] = None) -> None:
        if enabled_steps is None:
            self.enabled_steps = ["validation", "health", "simulation", "certification", "rollback", "drift"]
        else:
            self.enabled_steps = enabled_steps

        self.validation_engine = ValidationEngine()
        self.health_engine = HealthPrecheckEngine()
        self.simulation_engine = DryRunSimulationEngine()
        self.cert_engine = CertificationEngine()
        self.rollback_engine = RollbackEngine()
        self.drift_detector = DriftDetector()

    def run(self, context: ReliabilityContext) -> ReliabilityReport:
        val_rep = None
        health_rep = None
        sim_rep = None
        cert_rep = None
        roll_plan = None
        drift_rep = None

        if "validation" in self.enabled_steps:
            val_rep = self.validation_engine.execute_engine(context, before_validation, after_validation)

        if "health" in self.enabled_steps:
            health_rep = self.health_engine.execute_engine(context, before_health_check, after_health_check)

        if "simulation" in self.enabled_steps:
            sim_rep = self.simulation_engine.execute_engine(context, before_simulation, after_simulation)

        if "certification" in self.enabled_steps:
            cert_rep = self.cert_engine.execute_engine(context, before_certification, after_certification)

        if "rollback" in self.enabled_steps:
            roll_plan = self.rollback_engine.execute_engine(context, before_rollback_generation, after_rollback_generation)

        if "drift" in self.enabled_steps:
            # Use basic inline lambdas for lifecycle hooks
            drift_rep = self.drift_detector.execute_engine(context, lambda ctx: None, lambda ctx, rep: None)

        overall_risk = calculate_risk_assessment(context.diagnostics)
        
        # Report metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_pipeline"
        )

        return ReliabilityReport(
            metadata=report_meta,
            overall_risk=overall_risk,
            validation=val_rep,
            health=health_rep,
            simulation=sim_rep,
            certification=cert_rep,
            rollback=roll_plan,
            drift=drift_rep,
            diagnostics=tuple(context.diagnostics)
        )
