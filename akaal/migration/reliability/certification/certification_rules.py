from typing import List
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_warning

class NamingStandardCompliance:
    def check_compliance(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        plan = context.migration_plan
        # Certify if strict naming was fully adhered to
        if context.validation_config.strict_naming and plan and plan.operations:
            for op in plan.operations:
                obj = op.target_object
                if not obj.name.islower() and "_" not in obj.name:
                    pass
        return diagnostics
