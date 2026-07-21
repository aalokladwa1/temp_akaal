"""
AKAAL Platform 5 — ValidationPipeline Orchestrator

Sequentially executes the 5 validation pipeline stages, blocking execution on failure.
"""

from typing import Any, List

from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.domain.errors import ValidationError
from akaal.schema.validation.report import DiagnosticReport
from akaal.schema.validation.stages import (
    CompatibilityValidationStage,
    DependencyValidationStage,
    ExecutionPreCheckStage,
    PostExecutionValidationStage,
    SyntaxValidationStage,
)


class ValidationPipeline:
    """Sequential 5-Stage Validation Pipeline."""

    def __init__(self) -> None:
        self.stages = [
            SyntaxValidationStage(),
            DependencyValidationStage(),
            CompatibilityValidationStage(),
            ExecutionPreCheckStage(),
            PostExecutionValidationStage(),
        ]

    def validate(self, changes: List[BaseSchemaChange], schema_context: Any = None) -> DiagnosticReport:
        report = DiagnosticReport(is_valid=True)
        for stage in self.stages:
            passed = stage.validate(changes, schema_context, report)
            if not passed:
                report.is_valid = False
                raise ValidationError(
                    message=f"Validation failed at stage {stage.stage_type.value}.",
                    context={"stage": stage.stage_type.value, "diagnostics": [e.message for e in report.entries if not e.passed]},
                    recovery_recommendation="Fix schema syntax or dependency violations listed in diagnostic report."
                )
        return report
