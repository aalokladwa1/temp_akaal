"""
Akaal — Foreign Key Comparer
============================
Compares ForeignKeySchema definitions and generates ForeignKeyDifference models.
"""

from typing import Any, List, Optional
from akaal.core.comparison.comparers.base import BaseComparer
from akaal.core.comparison.models import (
    ForeignKeySchema,
    ForeignKeyDifference,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    generate_deterministic_id,
    ComparisonContext,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier


def get_fk_identity(fk: ForeignKeySchema, context: ComparisonContext) -> Any:
    """
    Computes a key identifier for a foreign key.
    If ignore_constraint_names is True, identity is based on columns and target table.
    Otherwise, identity is based on the resolved constraint name.
    """
    if context.ignore_constraint_names:
        return (
            tuple(resolve_identifier(c, context) for c in fk.from_columns),
            resolve_identifier(fk.to_table, context),
            tuple(resolve_identifier(c, context) for c in fk.to_columns),
        )
    return resolve_identifier(fk.name, context)


class ForeignKeyComparer(BaseComparer):
    """
    Sub-comparer responsible for comparing foreign key constraints.
    """
    OBJECT_TYPE = "FOREIGN_KEY"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares expected vs actual ForeignKeySchema.
        
        Expected kwargs:
            - table_name: Name of parent table.
        """
        if not isinstance(expected, ForeignKeySchema) or not isinstance(actual, ForeignKeySchema):
            return []

        table_name = kwargs.get("table_name", "unknown")
        fk_name = expected.name
        path = f"tables.{table_name}.foreign_keys.{fk_name}"

        differences: List[SchemaDifference] = []

        # Compare actions (ON DELETE, ON UPDATE)
        on_delete_mismatch = (expected.on_delete != actual.on_delete)
        on_update_mismatch = (expected.on_update != actual.on_update)

        # Names are structurally compared only if not ignored and they differed
        name_mismatch = False
        if not context.ignore_constraint_names:
            name_mismatch = (resolve_identifier(expected.name, context) != resolve_identifier(actual.name, context))

        if on_delete_mismatch or on_update_mismatch or name_mismatch:
            details = f"del={expected.on_delete}:upd={expected.on_update}->del={actual.on_delete}:upd={actual.on_update}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.FOREIGN_KEY.value,
                path=path,
                action=DifferenceAction.MODIFY.value,
                details=details,
            )
            
            # Action changes are high-risk constraint updates
            severity = DifferenceSeverity.CRITICAL
            impact = MigrationImpact.OFFLINE_DDL

            desc = f"Foreign key constraint '{fk_name}' on table '{table_name}' has mismatched attributes."
            if on_delete_mismatch:
                desc += f" Expected ON DELETE '{expected.on_delete}', got '{actual.on_delete}'."
            if on_update_mismatch:
                desc += f" Expected ON UPDATE '{expected.on_update}', got '{actual.on_update}'."

            # AI Planner Metadata (must create target table first)
            ai_metadata = {
                "dependency_paths": [f"tables.{expected.to_table}"],
                "remediation_state": {
                    "table_name": table_name,
                    "fk_name": expected.name,
                    "from_columns": expected.from_columns,
                    "to_table": expected.to_table,
                    "to_columns": expected.to_columns,
                    "on_delete": expected.on_delete,
                    "on_update": expected.on_update,
                    "actual_on_delete": actual.on_delete,
                    "actual_on_update": actual.on_update,
                }
            }

            differences.append(
                ForeignKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.FOREIGN_KEY,
                    action=DifferenceAction.MODIFY,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=desc,
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    fk_name=fk_name,
                    expected=expected,
                    actual=actual,
                )
            )

        return differences
