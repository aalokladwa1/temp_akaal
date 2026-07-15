from typing import List
from akaal.migration.models import ObjectType
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_warning

class SchemaValidator:
    """Validates structural differences between source and target schemas."""
    def validate_schema(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics: List[ReliabilityDiagnostic] = []
        report = context.schema_report
        
        if not report or not report.differences:
            return diagnostics

        for diff in report.differences:
            if diff.diff_type == "DROP" and diff.object_type == ObjectType.TABLE:
                diagnostics.append(
                    create_warning(
                        message=f"Destructive change detected: Table '{diff.object_name}' is scheduled to be dropped.",
                        category="SCHEMA",
                        recommendation="Back up the target database before executing schema changes."
                    )
                )
        return diagnostics
