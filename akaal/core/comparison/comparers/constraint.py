"""
Akaal — Constraint Comparer
===========================
Compares ConstraintSchema definitions and generates ConstraintDifference models.
"""

from typing import Any, List
from akaal.core.comparison.comparers.base import BaseComparer
from akaal.core.comparison.models import (
    ConstraintSchema,
    ConstraintDifference,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    generate_deterministic_id,
    ComparisonContext,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier


def get_constraint_identity(constraint: ConstraintSchema, context: ComparisonContext) -> Any:
    """
    Computes a key identifier for a unique or check constraint.
    If ignore_constraint_names is True, identity is based on columns or check definition.
    Otherwise, identity is based on the resolved name.
    """
    if context.ignore_constraint_names:
        if constraint.type == "UNIQUE":
            return ("UNIQUE", tuple(resolve_identifier(c, context) for c in constraint.columns))
        return ("CHECK", constraint.definition)
    return resolve_identifier(constraint.name, context)


class ConstraintComparer(BaseComparer):
    """
    Sub-comparer responsible for comparing UNIQUE and CHECK constraints.
    """
    OBJECT_TYPE = "CONSTRAINT"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares expected vs actual ConstraintSchema.
        
        Expected kwargs:
            - table_name: Name of parent table.
        """
        if not isinstance(expected, ConstraintSchema) or not isinstance(actual, ConstraintSchema):
            return []

        table_name = kwargs.get("table_name", "unknown")
        constraint_name = expected.name
        path = f"tables.{table_name}.constraints.{constraint_name}"

        differences: List[SchemaDifference] = []

        type_mismatch = (expected.type != actual.type)
        columns_mismatch = False
        definition_mismatch = False

        # If matched by name, we verify details
        if not context.ignore_constraint_names:
            exp_cols = tuple(resolve_identifier(c, context) for c in expected.columns)
            act_cols = tuple(resolve_identifier(c, context) for c in actual.columns)
            columns_mismatch = (exp_cols != act_cols)
            definition_mismatch = (expected.definition != actual.definition)

        if type_mismatch or columns_mismatch or definition_mismatch:
            details = f"type={expected.type}:cols={expected.columns}:def={expected.definition}->type={actual.type}:cols={actual.columns}:def={actual.definition}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.CONSTRAINT.value,
                path=path,
                action=DifferenceAction.MODIFY.value,
                details=details,
            )

            severity = DifferenceSeverity.CRITICAL
            impact = MigrationImpact.OFFLINE_DDL

            desc = f"Constraint '{constraint_name}' on table '{table_name}' has mismatched attributes."
            if type_mismatch:
                desc += f" Expected type {expected.type}, got {actual.type}."
            if columns_mismatch:
                desc += f" Expected columns {expected.columns}, got {actual.columns}."
            if definition_mismatch:
                desc += f" Expected check definition '{expected.definition}', got '{actual.definition}'."

            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "constraint_name": expected.name,
                    "type": expected.type,
                    "columns": expected.columns,
                    "definition": expected.definition,
                }
            }

            differences.append(
                ConstraintDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.CONSTRAINT,
                    action=DifferenceAction.MODIFY,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=desc,
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    constraint_name=constraint_name,
                    expected=expected,
                    actual=actual,
                )
            )

        return differences
