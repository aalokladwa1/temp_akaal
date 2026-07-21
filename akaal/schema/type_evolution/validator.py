"""
AKAAL Platform 5 — TypeEvolutionValidator

Validates type evolution safety against compatibility matrix.
"""

from akaal.schema.domain.errors import ValidationError
from akaal.schema.type_evolution.matrix import ConversionSafety
from akaal.schema.type_evolution.planner import ConversionPlan


class TypeEvolutionValidator:
    """Validates type evolution safety."""

    def validate_plan(self, plan: ConversionPlan) -> bool:
        if plan.safety == ConversionSafety.INCOMPATIBLE:
            raise ValidationError(
                message=f"Incompatible type evolution from '{plan.from_type}' to '{plan.to_type}'.",
                recovery_recommendation="Use custom data transformation or intermediate casting column."
            )
        return True
