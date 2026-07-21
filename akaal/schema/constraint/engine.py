"""
AKAAL Platform 5 — Constraint Evolution Subsystem

Handles Primary Keys, Foreign Keys, Unique, and Check constraint evolutions with dependency ordering.
"""

from typing import Any, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange, ChangeForeignKey, ChangePrimaryKey, AddUniqueConstraint, AddCheckConstraint
from akaal.schema.domain.errors import ValidationError
from akaal.schema.graph.dependency_graph import ConstraintDependencyGraph


class ConstraintPlanner:
    """Plans constraint evolution ordering ensuring FKs drop before PK changes and recreate afterwards."""

    def plan_constraint_changes(self, constraint_changes: List[BaseSchemaChange]) -> List[BaseSchemaChange]:
        dep_graph = ConstraintDependencyGraph()
        for ch in constraint_changes:
            dep_graph.add_change(ch)
        return dep_graph.compute_execution_order()


class ConstraintValidator:
    """Validates constraint definitions before evolution."""

    def validate_constraints(self, constraint_changes: List[BaseSchemaChange]) -> bool:
        for ch in constraint_changes:
            v_res = ch.validate(None)
            if not v_res.is_valid:
                raise ValidationError(
                    message=f"Constraint validation error in change '{ch.change_id}': {v_res.errors}",
                    recovery_recommendation="Verify constraint column names and foreign key references."
                )
        return True


class ConstraintEvolutionEngine:
    """Enterprise Constraint Evolution Engine."""

    def __init__(self) -> None:
        self.planner = ConstraintPlanner()
        self.validator = ConstraintValidator()

    def evolve_constraints(self, constraint_changes: List[BaseSchemaChange], db_context: Any = None) -> List[BaseSchemaChange]:
        self.validator.validate_constraints(constraint_changes)
        ordered_changes = self.planner.plan_constraint_changes(constraint_changes)

        for ch in ordered_changes:
            ch.execute(db_context)

        return ordered_changes
