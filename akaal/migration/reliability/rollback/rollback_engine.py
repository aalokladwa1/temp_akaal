import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.rollback_report import RollbackPlan
from akaal.migration.reliability.artifacts.rollback_artifact import RollbackArtifact
from akaal.migration.reliability.rollback.rollback_planner import RollbackPlanner
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment
from akaal.migration.reliability.utilities.diagnostics import create_warning

class RollbackEngine(BaseReliabilityEngine):
    """
    RollbackEngine compiles reverse-migration sequences, constructs topological drop trees,
    and assesses the hazard risk of automated database rollbacks.
    """
    def __init__(self) -> None:
        super().__init__(name="rollback")
        self.planner = RollbackPlanner()

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> RollbackPlan:
        plan = context.migration_plan

        # Formulate steps and safety flags
        steps, safe = self.planner.plan_rollback(plan)

        if not safe:
            diagnostics.append(
                create_warning(
                    message="Rollback plan contains destructive reversals (creating dropped tables requires backups).",
                    category="ROLLBACK",
                    recommendation="Ensure point-in-time recovery (PITR) is active before execution."
                )
            )

        # Risk assessment
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build report audit metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_rollback"
        )

        # Artifact construction (machine-consumable)
        artifact = RollbackArtifact(
            execution_id=report_meta.execution_id,
            step_count=len(steps),
            rollback_possible=safe
        )

        return RollbackPlan(
            metadata=report_meta,
            steps=tuple(steps),
            safe_to_rollback=safe,
            risk=risk_assessment
        )
