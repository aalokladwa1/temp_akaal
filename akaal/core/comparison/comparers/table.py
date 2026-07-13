"""
Akaal — Table Comparer
======================
Compares TableSchema definitions and delegates column, index, key, and constraint checks.
"""

from typing import Any, Dict, List, Optional, Set
from akaal.core.comparison.comparers.base import BaseComparer, COMPARER_REGISTRY
from akaal.core.comparison.models import (
    TableSchema,
    TableDifference,
    ColumnDifference,
    ForeignKeyDifference,
    IndexDifference,
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
from akaal.core.comparison.comparers.foreign_key import get_fk_identity
from akaal.core.comparison.comparers.index import get_index_identity
from akaal.core.comparison.comparers.constraint import get_constraint_identity


class TableComparer(BaseComparer):
    """
    Orchestrates the comparison of a single database table.
    Delegates element comparisons to corresponding sub-comparers via COMPARER_REGISTRY.
    """
    OBJECT_TYPE = "TABLE"

    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares expected vs actual TableSchema.
        """
        # Safe casting
        exp_table: Optional[TableSchema] = expected if isinstance(expected, TableSchema) else None
        act_table: Optional[TableSchema] = actual if isinstance(actual, TableSchema) else None

        if exp_table is None and act_table is None:
            return []

        differences: List[SchemaDifference] = []

        # 1. ADD Table (Present in expected, missing in actual)
        if exp_table is not None and act_table is None:
            table_name = exp_table.name
            path = f"tables.{table_name}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.TABLE.value,
                path=path,
                action=DifferenceAction.ADD.value,
            )
            # Find dependencies: all tables referenced in foreign keys must exist first
            dependencies = [resolve_identifier(fk.to_table, context) for fk in exp_table.foreign_keys]
            ai_metadata = {
                "dependency_paths": [f"tables.{dep}" for dep in dependencies],
                "remediation_state": {
                    "table_name": table_name,
                    # Serialization models will capture DDL generation parameters
                }
            }

            differences.append(
                TableDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.TABLE,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.ONLINE_DDL,  # Creating tables is safe
                    description=f"Table '{table_name}' is missing.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    expected=exp_table,
                    actual=None,
                )
            )
            return differences

        # 2. REMOVE Table (Missing in expected, present in actual)
        if exp_table is None and act_table is not None:
            table_name = act_table.name
            path = f"tables.{table_name}"
            diff_id = generate_deterministic_id(
                category=DifferenceCategory.TABLE.value,
                path=path,
                action=DifferenceAction.REMOVE.value,
            )
            ai_metadata = {
                "dependency_paths": [],  # Clean drop
                "remediation_state": {
                    "table_name": table_name,
                }
            }

            differences.append(
                TableDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.TABLE,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.DESTRUCTIVE,  # Dropping tables destroys data
                    description=f"Table '{table_name}' is unexpected.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    expected=None,
                    actual=act_table,
                )
            )
            return differences

        # 3. MODIFY Table (Present in both, check attributes)
        assert exp_table is not None and act_table is not None
        table_name = exp_table.name

        # Resolve Sub-comparers
        column_comparer = COMPARER_REGISTRY["COLUMN"]()
        pk_comparer = COMPARER_REGISTRY["PRIMARY_KEY"]()
        fk_comparer = COMPARER_REGISTRY["FOREIGN_KEY"]()
        index_comparer = COMPARER_REGISTRY["INDEX"]()
        constraint_comparer = COMPARER_REGISTRY["CONSTRAINT"]()

        # Gather Primary Key Column Names (for default mapping check)
        pk_columns: Set[str] = set()
        if exp_table.primary_key:
            pk_columns.update(resolve_identifier(c, context) for c in exp_table.primary_key.columns)

        # 3.1. Columns Comparison
        exp_cols_dict = {resolve_identifier(col.name, context): col for col in exp_table.columns}
        act_cols_dict = {resolve_identifier(col.name, context): col for col in act_table.columns}

        # Columns Added / Removed
        for col_name in sorted(exp_cols_dict.keys() - act_cols_dict.keys()):
            col = exp_cols_dict[col_name]
            path = f"tables.{table_name}.columns.{col.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.COLUMN.value, path, DifferenceAction.ADD.value)
            
            # Severity is critical if adding a NOT NULL column without default
            is_nullable = col.nullable
            has_default = (col.default_value is not None and col.default_value != "NULL")
            severity = DifferenceSeverity.WARNING if (is_nullable or has_default) else DifferenceSeverity.CRITICAL
            impact = MigrationImpact.OFFLINE_DDL

            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "column_name": col.name,
                    "expected": {
                        "type": col.data_type,
                        "raw_type": col.raw_type,
                        "nullable": col.nullable,
                        "default": col.default_value,
                    }
                }
            }
            differences.append(
                ColumnDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.COLUMN,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=f"Table '{table_name}' is missing column '{col.name}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    column_name=col.name,
                    expected=col,
                    actual=None,
                )
            )

        for col_name in sorted(act_cols_dict.keys() - exp_cols_dict.keys()):
            col = act_cols_dict[col_name]
            path = f"tables.{table_name}.columns.{col.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.COLUMN.value, path, DifferenceAction.REMOVE.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "column_name": col.name,
                }
            }
            differences.append(
                ColumnDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.COLUMN,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.CRITICAL,
                    impact=MigrationImpact.DESTRUCTIVE,  # Dropping columns deletes data
                    description=f"Table '{table_name}' has unexpected column '{col.name}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    column_name=col.name,
                    expected=None,
                    actual=col,
                )
            )

        # Columns Modified
        for col_name in sorted(exp_cols_dict.keys() & act_cols_dict.keys()):
            exp_col = exp_cols_dict[col_name]
            act_col = act_cols_dict[col_name]
            col_is_pk = (col_name in pk_columns)
            
            col_diffs = column_comparer.compare(
                exp_col,
                act_col,
                context,
                table_name=table_name,
                is_pk=col_is_pk,
            )
            differences.extend(col_diffs)

        # 3.2. Primary Key Comparison
        pk_diffs = pk_comparer.compare(
            exp_table.primary_key,
            act_table.primary_key,
            context,
            table_name=table_name,
        )
        differences.extend(pk_diffs)

        # 3.3. Foreign Keys Comparison
        exp_fks = {get_fk_identity(fk, context): fk for fk in exp_table.foreign_keys}
        act_fks = {get_fk_identity(fk, context): fk for fk in act_table.foreign_keys}

        for fk_id in sorted(exp_fks.keys() - act_fks.keys(), key=str):
            fk = exp_fks[fk_id]
            path = f"tables.{table_name}.foreign_keys.{fk.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.FOREIGN_KEY.value, path, DifferenceAction.ADD.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{fk.to_table}"],
                "remediation_state": {
                    "table_name": table_name,
                    "fk_name": fk.name,
                    "from_columns": fk.from_columns,
                    "to_table": fk.to_table,
                    "to_columns": fk.to_columns,
                }
            }
            differences.append(
                ForeignKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.FOREIGN_KEY,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=DifferenceSeverity.WARNING,
                    impact=MigrationImpact.OFFLINE_DDL,
                    description=f"Table '{table_name}' is missing foreign key constraint '{fk.name}' referencing '{fk.to_table}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    fk_name=fk.name,
                    expected=fk,
                    actual=None,
                )
            )

        for fk_id in sorted(act_fks.keys() - exp_fks.keys(), key=str):
            fk = act_fks[fk_id]
            path = f"tables.{table_name}.foreign_keys.{fk.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.FOREIGN_KEY.value, path, DifferenceAction.REMOVE.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "fk_name": fk.name,
                }
            }
            differences.append(
                ForeignKeyDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.FOREIGN_KEY,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.WARNING,
                    impact=MigrationImpact.ONLINE_DDL,
                    description=f"Table '{table_name}' has unexpected foreign key constraint '{fk.name}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    fk_name=fk.name,
                    expected=None,
                    actual=fk,
                )
            )

        for fk_id in sorted(exp_fks.keys() & act_fks.keys(), key=str):
            differences.extend(
                fk_comparer.compare(
                    exp_fks[fk_id],
                    act_fks[fk_id],
                    context,
                    table_name=table_name,
                )
            )

        # 3.4. Indexes Comparison
        exp_idxs = {get_index_identity(idx, context): idx for idx in exp_table.indexes}
        act_idxs = {get_index_identity(idx, context): idx for idx in act_table.indexes}

        for idx_id in sorted(exp_idxs.keys() - act_idxs.keys(), key=str):
            idx = exp_idxs[idx_id]
            path = f"tables.{table_name}.indexes.{idx.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.INDEX.value, path, DifferenceAction.ADD.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "index_name": idx.name,
                    "columns": idx.columns,
                    "unique": idx.unique,
                }
            }
            differences.append(
                IndexDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.INDEX,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=DifferenceSeverity.WARNING,
                    impact=MigrationImpact.ONLINE_DDL,
                    description=f"Table '{table_name}' is missing index '{idx.name}' on columns {idx.columns}.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    index_name=idx.name,
                    expected=idx,
                    actual=None,
                )
            )

        for idx_id in sorted(act_idxs.keys() - exp_idxs.keys(), key=str):
            idx = act_idxs[idx_id]
            path = f"tables.{table_name}.indexes.{idx.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.INDEX.value, path, DifferenceAction.REMOVE.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "index_name": idx.name,
                }
            }
            differences.append(
                IndexDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.INDEX,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.WARNING,
                    impact=MigrationImpact.ONLINE_DDL,
                    description=f"Table '{table_name}' has unexpected index '{idx.name}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    index_name=idx.name,
                    expected=None,
                    actual=idx,
                )
            )

        for idx_id in sorted(exp_idxs.keys() & act_idxs.keys(), key=str):
            differences.extend(
                index_comparer.compare(
                    exp_idxs[idx_id],
                    act_idxs[idx_id],
                    context,
                    table_name=table_name,
                )
            )

        # 3.5. Constraints Comparison (UNIQUE and CHECK constraints)
        exp_consts = {get_constraint_identity(c, context): c for c in exp_table.constraints}
        act_consts = {get_constraint_identity(c, context): c for c in act_table.constraints}

        for const_id in sorted(exp_consts.keys() - act_consts.keys(), key=str):
            const = exp_consts[const_id]
            path = f"tables.{table_name}.constraints.{const.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.CONSTRAINT.value, path, DifferenceAction.ADD.value)
            
            # Severity is critical for unique constraints or checks that might cause insert failures
            severity = DifferenceSeverity.CRITICAL if const.type == "UNIQUE" else DifferenceSeverity.WARNING
            impact = MigrationImpact.OFFLINE_DDL

            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "constraint_name": const.name,
                    "type": const.type,
                    "columns": const.columns,
                    "definition": const.definition,
                }
            }
            differences.append(
                ConstraintDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.CONSTRAINT,
                    action=DifferenceAction.ADD,
                    path=path,
                    severity=severity,
                    impact=impact,
                    description=f"Table '{table_name}' is missing constraint '{const.name}' of type {const.type}.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    constraint_name=const.name,
                    expected=const,
                    actual=None,
                )
            )

        for const_id in sorted(act_consts.keys() - exp_consts.keys(), key=str):
            const = act_consts[const_id]
            path = f"tables.{table_name}.constraints.{const.name}"
            diff_id = generate_deterministic_id(DifferenceCategory.CONSTRAINT.value, path, DifferenceAction.REMOVE.value)
            ai_metadata = {
                "dependency_paths": [f"tables.{table_name}"],
                "remediation_state": {
                    "table_name": table_name,
                    "constraint_name": const.name,
                }
            }
            differences.append(
                ConstraintDifference(
                    difference_id=diff_id,
                    category=DifferenceCategory.CONSTRAINT,
                    action=DifferenceAction.REMOVE,
                    path=path,
                    severity=DifferenceSeverity.WARNING,
                    impact=MigrationImpact.OFFLINE_DDL,
                    description=f"Table '{table_name}' has unexpected constraint '{const.name}'.",
                    ai_metadata=ai_metadata,
                    table_name=table_name,
                    constraint_name=const.name,
                    expected=None,
                    actual=const,
                )
            )

        for const_id in sorted(exp_consts.keys() & act_consts.keys(), key=str):
            differences.extend(
                constraint_comparer.compare(
                    exp_consts[const_id],
                    act_consts[const_id],
                    context,
                    table_name=table_name,
                )
            )

        return differences
