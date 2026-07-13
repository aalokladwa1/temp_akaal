"""
Akaal — Column Comparer
=======================
Compares ColumnSchema definitions and generates ColumnDifference models.
"""

from typing import Any, List
from akaal.core.comparison.comparers.base import BaseComparer
from akaal.core.comparison.models import (
    ColumnSchema,
    ColumnDifference,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    generate_deterministic_id,
    ComparisonContext,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier
from akaal.core.comparison.support.equivalence_rules import are_types_equivalent, are_defaults_equivalent


class ColumnComparer(BaseComparer):
    """
    Sub-comparer responsible for detecting differences between two columns.
    """
    OBJECT_TYPE = "COLUMN"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares ColumnSchema attributes.
        
        Expected kwargs:
            - table_name: Name of parent table.
            - is_pk: Boolean indicating if this column belongs to the primary key.
        """
        if not isinstance(expected, ColumnSchema) or not isinstance(actual, ColumnSchema):
            return []

        table_name = kwargs.get("table_name", "unknown")
        is_pk = kwargs.get("is_pk", False)

        path = f"tables.{table_name}.columns.{expected.name}"
        differences: List[SchemaDifference] = []

        # 1. Type check
        type_mismatch = not are_types_equivalent(
            expected.data_type, actual.data_type, expected.raw_type, actual.raw_type, context
        )

        # 2. Nullability check
        nullability_mismatch = (expected.nullable != actual.nullable)

        # 3. Default expression check
        default_mismatch = not are_defaults_equivalent(
            expected.default_value or "NULL",
            actual.default_value or "NULL",
            expected.data_type,
            actual.data_type,
            is_pk,
        )

        if type_mismatch or nullability_mismatch or default_mismatch:
            # Determine severity and impact
            if type_mismatch:
                severity = DifferenceSeverity.CRITICAL
                impact = MigrationImpact.DESTRUCTIVE
                desc = f"Column '{expected.name}' type mismatch on table '{table_name}'. Expected {expected.raw_type}, got {actual.raw_type}."
            elif nullability_mismatch:
                # Making a column NOT NULL is higher risk than making it NULL
                if not expected.nullable:
                    severity = DifferenceSeverity.CRITICAL
                    impact = MigrationImpact.OFFLINE_DDL
                    desc = f"Column '{expected.name}' changed to NOT NULL on table '{table_name}'."
                else:
                    severity = DifferenceSeverity.WARNING
                    impact = MigrationImpact.ONLINE_DDL
                    desc = f"Column '{expected.name}' changed to NULL on table '{table_name}'."
            else:
                severity = DifferenceSeverity.WARNING
                impact = MigrationImpact.ONLINE_DDL
                desc = f"Column '{expected.name}' default mismatch on table '{table_name}'. Expected {expected.default_value}, got {actual.default_value}."

            details = f"type={expected.data_type}:{expected.nullable}:{expected.default_value}->{actual.data_type}:{actual.nullable}:{actual.default_value}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.COLUMN.value,
                path=path,
                action=DifferenceAction.MODIFY.value,
                details=details,
            )

            # Build AI Planner Metadata
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "column_name": expected.name,
                    "expected_type": expected.data_type,
                    "expected_raw_type": expected.raw_type,
                    "expected_nullable": expected.nullable,
                    "expected_default": expected.default_value,
                    "actual_type": actual.data_type,
                    "actual_raw_type": actual.raw_type,
                    "actual_nullable": actual.nullable,
                    "actual_default": actual.default_value,
                }
            }

            differences.append(
                ColumnDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.COLUMN,
                    action=DifferenceAction.MODIFY,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=desc,
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    column_name=expected.name,
                    expected=expected,
                    actual=actual,
                    type_mismatch=type_mismatch,
                    nullability_mismatch=nullability_mismatch,
                    default_mismatch=default_mismatch,
                )
            )

        return differences
