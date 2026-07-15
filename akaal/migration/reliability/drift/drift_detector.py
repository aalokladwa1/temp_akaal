import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.drift_report import DriftReport
from akaal.migration.reliability.artifacts.drift_artifact import DriftArtifact
from akaal.migration.reliability.drift.drift_registry import DriftRegistry
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment
from akaal.migration.reliability.utilities.diagnostics import create_warning

class DriftDetector(BaseReliabilityEngine):
    """
    DriftDetector compares active target database metadata against planned target states
    to identify unauthorized structural, constraint, or index modifications.
    """
    def __init__(self) -> None:
        super().__init__(name="drift")

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> DriftReport:
        drifts = []
        has_drift = False

        # Scan differences in SchemaComparisonReport
        report = context.schema_report
        plan = context.migration_plan
        
        planned_objects = set()
        if plan and plan.operations:
            for op in plan.operations:
                planned_objects.add(op.target_object.name)

        if report and report.differences:
            for diff in report.differences:
                # If target object has a difference but is not part of planned operations, it represents drift!
                if diff.object_name not in planned_objects:
                    has_drift = True
                    drifts.append(f"Object '{diff.object_name}' (type: {diff.object_type}) has ad-hoc difference: {diff.diff_type}")
                    diagnostics.append(
                        create_warning(
                            message=f"Drift detected: Object '{diff.object_name}' has unscheduled difference '{diff.diff_type}'.",
                            category="DRIFT",
                            recommendation="Synchronize schemas or revert ad-hoc changes before proceeding."
                        )
                    )

        # Run registered drift scanners
        for scanner_name, scanner_instance in DriftRegistry.get_scanners().items():
            scanner_diags = scanner_instance.scan(context)
            if scanner_diags:
                has_drift = True
                diagnostics.extend(scanner_diags)
                drifts.append(f"Scanner '{scanner_name}' detected metadata changes.")

        # Risk assessment
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build report audit metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_drift"
        )

        # Artifact construction (machine-consumable)
        artifact = DriftArtifact(
            execution_id=report_meta.execution_id,
            drift_detected=has_drift,
            drifted_objects=drifts
        )

        return DriftReport(
            metadata=report_meta,
            has_drift=has_drift,
            drifts=tuple(drifts),
            risk=risk_assessment
        )
