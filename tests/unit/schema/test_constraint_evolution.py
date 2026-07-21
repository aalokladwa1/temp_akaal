"""
Unit tests for Feature 7 — Constraint Evolution.
"""

import pytest

from akaal.schema.constraint.engine import ConstraintEvolutionEngine, ConstraintPlanner
from akaal.schema.domain.changes import ChangeForeignKey, ChangePrimaryKey
from akaal.schema.domain.identifiers import SchemaIdentifier


class DummyDBContext:
    def __init__(self) -> None:
        self.executed = []

    def execute_statement(self, sql: str) -> None:
        self.executed.append(sql)


def test_constraint_planner_and_execution():
    engine = ConstraintEvolutionEngine()
    db = DummyDBContext()

    t_parent = SchemaIdentifier("public", "parent_tbl")
    t_child = SchemaIdentifier("public", "child_tbl")

    pk_ch = ChangePrimaryKey(t_parent, new_pk_columns=["id"])
    fk_ch = ChangeForeignKey(t_child, constraint_name="fk_child_parent", fk_columns=["p_id"], ref_table="parent_tbl", ref_columns=["id"])

    res = engine.evolve_constraints([pk_ch, fk_ch], db_context=db)
    assert len(res) == 2
    assert len(db.executed) >= 2
