"""
Akaal — Primary Key Comparer
============================
Compares PrimaryKeySchema definitions and generates PrimaryKeyDifference models.
"""

from typing import Any, List, Optional
from akaal.core.comparison.comparers.base import BaseComparer
from akaal.core.comparison.models import (
    PrimaryKeySchema,
    PrimaryKeyDifference,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    generate_deterministic_id,
    ComparisonContext,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier


class PrimaryKeyComparer(BaseComparer):
    """
    Sub-comparer responsible for detecting differences between primary key constraints.
    """
    OBJECT_TYPE = "PRIMARY_KEY"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares expected vs actual PrimaryKeySchema.
        
        Expected kwargs:
            - table_name: Name of parent table.
        """
        table_name = kwargs.get("table_name", "unknown")
        path = f"tables.{table_name}.primary_key"
        
        # Safe casting
        exp_pk: Optional[PrimaryKeySchema] = expected if isinstance(expected, PrimaryKeySchema) else None
        act_pk: Optional[PrimaryKeySchema] = actual if isinstance(actual, PrimaryKeySchema) else None

        if exp_pk is None and act_pk is None:
            return []

        # 1. ADD Primary Key
        if exp_pk is not None and act_pk is None:
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.PRIMARY_KEY.value,
                path=path,
                action=DifferenceAction.ADD.value,
            )
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "columns": exp_pk.columns,
                    "name": exp_pk.name,
                }
            }
            return [
                PrimaryKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.PRIMARY_KEY,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.OFFLINE_DDL,
                    description=f"Table '{table_name}' is missing primary key constraint on columns {exp_pk.columns}.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    expected=exp_pk,
                    actual=None,
                )
            ]

        # 2. REMOVE Primary Key
        if exp_pk is None and act_pk is not None:
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.PRIMARY_KEY.value,
                path=path,
                action=DifferenceAction.REMOVE.value,
            )
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "columns": act_pk.columns,
                    "name": act_pk.name,
                }
            }
            return [
                PrimaryKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.PRIMARY_KEY,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.DESTRUCTIVE,
                    description=f"Table '{table_name}' has an unexpected primary key constraint on columns {act_pk.columns}.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    expected=None,
                    actual=act_pk,
                )
            ]

        # 3. MODIFY Primary Key (both present but mismatching)
        assert exp_pk is not None and act_pk is not None
        exp_cols = tuple(resolve_identifier(c, context) for c in exp_pk.columns)
        act_cols = tuple(resolve_identifier(c, context) for c in act_pk.columns)

        if exp_cols != act_cols:
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.PRIMARY_KEY.value,
                path=path,
                action=DifferenceAction.MODIFY.value,
            )
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "expected_columns": exp_pk.columns,
                    "actual_columns": act_pk.columns,
                    "expected_name": exp_pk.name,
                    "actual_name": act_pk.name,
                }
            }
            return [
                PrimaryKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.PRIMARY_KEY,
                    action=DifferenceAction.MODIFY,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.OFFLINE_DDL,
                    description=f"Table '{table_name}' primary key columns mismatch. Expected columns {exp_pk.columns}, got {act_pk.columns}.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    expected=exp_pk,
                    actual=act_pk,
                )
            ]

        return []
