from typing import List
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_warning

class CapacityHealthCheck:
    def check(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        plan = context.migration_plan
        # Warn if the plan contains over 10 table creations as it indicates high capacity requirements
        if plan and plan.operations:
            tables_created = sum(1 for op in plan.operations if op.operation_type == "CREATE" and op.target_object.object_type == "TABLE")
            if tables_created > 10:
                diagnostics.append(
                    create_warning(
                        message=f"Plan contains {tables_created} table creations. High storage growth expected.",
                        category="CAPACITY",
                        recommendation="Verify storage space on target database volume."
                    )
                )
        return diagnostics
