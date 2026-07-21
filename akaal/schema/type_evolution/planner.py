"""
AKAAL Platform 5 — ConversionPlanner & Strategy Generator

Generates two-phase conversion plans for type widening and shadow-column conversion for narrowing.
"""

from dataclasses import dataclass, field
from typing import List

from akaal.schema.domain.changes import DDLStatement
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.type_evolution.matrix import ConversionSafety, TypeCompatibilityMatrix


@dataclass
class ConversionPlan:
    from_type: str
    to_type: str
    safety: ConversionSafety
    forward_steps: List[DDLStatement] = field(default_factory=list)
    rollback_steps: List[DDLStatement] = field(default_factory=list)


class ConversionPlanner:
    """Generates execution & rollback steps for type evolution."""

    def plan_conversion(self, target_table: SchemaIdentifier, column_name: str, from_type: str, to_type: str) -> ConversionPlan:
        safety = TypeCompatibilityMatrix.evaluate_conversion(from_type, to_type)

        if safety == ConversionSafety.SAFE_WIDENING:
            sql_fwd = f"ALTER TABLE {target_table} ALTER COLUMN {column_name} TYPE {to_type};"
            sql_rev = f"ALTER TABLE {target_table} ALTER COLUMN {column_name} TYPE {from_type};"
            return ConversionPlan(
                from_type=from_type,
                to_type=to_type,
                safety=safety,
                forward_steps=[DDLStatement(sql=sql_fwd, target_object=str(target_table))],
                rollback_steps=[DDLStatement(sql=sql_rev, target_object=str(target_table))],
            )
        elif safety == ConversionSafety.UNSAFE_NARROWING:
            temp_col = f"{column_name}_temp"
            fwd_stmts = [
                DDLStatement(sql=f"ALTER TABLE {target_table} ADD COLUMN {temp_col} {to_type};", target_object=str(target_table)),
                DDLStatement(sql=f"UPDATE {target_table} SET {temp_col} = CAST({column_name} AS {to_type});", target_object=str(target_table)),
                DDLStatement(sql=f"ALTER TABLE {target_table} DROP COLUMN {column_name};", target_object=str(target_table), is_destructive=True),
                DDLStatement(sql=f"ALTER TABLE {target_table} RENAME COLUMN {temp_col} TO {column_name};", target_object=str(target_table)),
            ]
            rev_stmts = [
                DDLStatement(sql=f"ALTER TABLE {target_table} ALTER COLUMN {column_name} TYPE {from_type};", target_object=str(target_table))
            ]
            return ConversionPlan(
                from_type=from_type,
                to_type=to_type,
                safety=safety,
                forward_steps=fwd_stmts,
                rollback_steps=rev_stmts,
            )
        else:
            return ConversionPlan(from_type=from_type, to_type=to_type, safety=safety)
