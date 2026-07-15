import time
from typing import List
from akaal.migration.reliability.base import BaseReliabilityEngine
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.report_metadata import ReportMetadata
from akaal.migration.reliability.reports.validation_report import ValidationReport
from akaal.migration.reliability.artifacts.validation_artifact import ValidationArtifact
from akaal.migration.reliability.validation.registry import ObjectValidatorRegistry
from akaal.migration.reliability.validation.schema_validator import SchemaValidator
from akaal.migration.reliability.validation.integrity_validator import IntegrityValidator
from akaal.migration.reliability.validation.data_quality_validator import DataQualityValidator
from akaal.migration.reliability.plugins.registry import PluginRegistry
from akaal.migration.reliability.utilities.scoring import calculate_risk_assessment

class ValidationEngine(BaseReliabilityEngine):
    """
    ValidationEngine runs all metadata-based schema, integrity,
    and data quality validator checks, producing human and machine reports.
    """
    def __init__(self) -> None:
        super().__init__(name="validation")
        self.schema_validator = SchemaValidator()
        self.integrity_validator = IntegrityValidator()
        self.data_quality_validator = DataQualityValidator()

    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> ValidationReport:
        # 1. Schema diff validations
        diagnostics.extend(self.schema_validator.validate_schema(context))
        
        # 2. Integrity constraints validations
        diagnostics.extend(self.integrity_validator.validate_integrity(context))
        
        # 3. Data quality validations
        diagnostics.extend(self.data_quality_validator.validate_quality(context))

        # 4. Run Object-level Validators registered in registry
        plan = context.migration_plan
        if plan and plan.operations:
            for op in plan.operations:
                obj = op.target_object
                try:
                    validator = ObjectValidatorRegistry.get_validator(obj.object_type)
                    diagnostics.extend(validator.validate_object(obj, context))
                except ValueError:
                    # Ignore unregistered object types
                    pass

        # 5. Run registered third-party plugins
        for plugin in PluginRegistry.get_validators():
            diagnostics.extend(plugin.validate(context))

        # Determine success
        success = not any(d.severity == "ERROR" for d in diagnostics)
        
        # Risk assessment
        risk_assessment = calculate_risk_assessment(diagnostics)

        # Build metadata
        report_meta = ReportMetadata(
            engine_version="1.0.0",
            schema_version="1.0.0",
            generated_at=time.time(),
            execution_id=context.execution_context.get_metadata("execution_id", "exec_dev") if context.execution_context else "exec_dev",
            report_id="rpt_val"
        )

        # Aggregate report
        report = ValidationReport(
            metadata=report_meta,
            success=success,
            diagnostics=tuple(diagnostics),
            risk=risk_assessment
        )

        # Artifact construction (machine-consumable)
        artifact = ValidationArtifact(
            execution_id=report_meta.execution_id,
            passed=success,
            error_count=sum(1 for d in diagnostics if d.severity == "ERROR"),
            warning_count=sum(1 for d in diagnostics if d.severity == "WARNING"),
            raw_metrics={"diagnostic_count": len(diagnostics)}
        )
        # Expose it for execution pipelines if needed
        pass

        return report
