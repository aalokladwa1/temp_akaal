"""
Akaal — Index Comparer
======================
Compares IndexSchema definitions and generates IndexDifference models.
"""

from typing import Any, List
from akaal.core.comparison.comparers.base import BaseComparer
from akaal.core.comparison.models import (
    IndexSchema,
    IndexDifference,
    DifferenceCategory,
    DifferenceAction,
    DifferenceSeverity,
    MigrationImpact,
    SchemaDifference,
    generate_deterministic_id,
    ComparisonContext,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier


def get_index_identity(index: IndexSchema, context: ComparisonContext) -> Any:
    """
    Computes a key identifier for an index.
    If ignore_index_names is True, identity is based on columns.
    Otherwise, identity is based on the resolved index name.
    """
    if context.ignore_index_names:
        return tuple(resolve_identifier(c, context) for c in index.columns)
    return resolve_identifier(index.name, context)


class IndexComparer(BaseComparer):
    """
    Sub-comparer responsible for comparing database indexes.
    """
    OBJECT_TYPE = "INDEX"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares expected vs actual IndexSchema.
        
        Expected kwargs:
            - table_name: Name of parent table.
        """
        if not isinstance(expected, IndexSchema) or not isinstance(actual, IndexSchema):
            return []

        table_name = kwargs.get("table_name", "unknown")
        index_name = expected.name
        path = f"tables.{table_name}.indexes.{index_name}"

        differences: List[SchemaDifference] = []

        uniqueness_mismatch = (expected.unique != actual.unique)

        # Name mismatch under strict index names
        name_mismatch = False
        if not context.ignore_index_names:
            name_mismatch = (resolve_identifier(expected.name, context) != resolve_identifier(actual.name, context))

        if uniqueness_mismatch or name_mismatch:
            details = f"uniq={expected.unique}->uniq={actual.unique}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.INDEX.value,
                path=path,
                action=DifferenceAction.MODIFY.value,
                details=details,
            )

            # Changing uniqueness requires dropping and recreating the index
            severity = DifferenceSeverity.CRITICAL
            impact = MigrationImpact.OFFLINE_DDL

            desc = f"Index '{index_name}' on table '{table_name}' has mismatched attributes."
            if uniqueness_mismatch:
                desc += f" Expected unique={expected.unique}, got unique={actual.unique}."

            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "index_name": expected.name,
                    "columns": expected.columns,
                    "unique": expected.unique,
                    "actual_unique": actual.unique,
                }
            }

            differences.append(
                IndexDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.INDEX,
                    action=DifferenceAction.MODIFY,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=desc,
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    index_name=index_name,
                    expected=expected,
                    actual=actual,
                    uniqueness_mismatch=uniqueness_mismatch,
                )
            )

        return differences
