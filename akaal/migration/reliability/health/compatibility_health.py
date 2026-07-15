from typing import List
from akaal.migration.models import ObjectType
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_error

class CompatibilityHealthCheck:
    def check(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        plan = context.migration_plan
        capabilities = context.capabilities
        if plan and plan.operations and capabilities:
            for op in plan.operations:
                obj = op.target_object
                # Verify capabilities constraints
                if obj.object_type == ObjectType.SEQUENCE and not getattr(capabilities, "supports_sequence_increment", True):
                    diagnostics.append(
                        create_error(
                            message=f"Target database capabilities do not support Sequence incremental adjustments for '{obj.name}'.",
                            category="COMPATIBILITY",
                            recommendation="Convert Sequences to identity columns or native SERIAL types."
                        )
                    )
        return diagnostics
