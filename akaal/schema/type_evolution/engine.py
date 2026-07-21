"""
AKAAL Platform 5 — TypeEvolutionValidator & TypeEvolutionEngine

Orchestrates type evolution planning and validation.
"""

from typing import Optional

from akaal.schema.domain.errors import ValidationError
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.type_evolution.matrix import ConversionSafety
from akaal.schema.type_evolution.planner import ConversionPlan, ConversionPlanner
from akaal.schema.type_evolution.validator import TypeEvolutionValidator


class TypeEvolutionValidator:
    """Validates type evolution safety."""

    def validate_plan(self, plan: ConversionPlan) -> bool:
        if plan.safety == ConversionSafety.INCOMPATIBLE:
            raise ValidationError(
                message=f"Incompatible type evolution from '{plan.from_type}' to '{plan.to_type}'.",
                recovery_recommendation="Use custom data transformation or intermediate casting column."
            )
        return True


class TypeEvolutionEngine:
    """Engine executing online type evolution planning and safety validation."""

    def __init__(self) -> None:
        self.planner = ConversionPlanner()
        self.validator = TypeEvolutionValidator()

    def plan_and_validate(self, target_table: SchemaIdentifier, column_name: str, from_type: str, to_type: str) -> ConversionPlan:
        plan = self.planner.plan_conversion(target_table, column_name, from_type, to_type)
        self.validator.validate_plan(plan)
        return plan
