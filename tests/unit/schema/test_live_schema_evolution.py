"""
Unit tests for Feature 5 — Live Schema Evolution & Transactions.
"""

import pytest

from akaal.schema.domain.changes import AddColumn, AddTable
from akaal.schema.domain.enums import TransactionState
from akaal.schema.domain.errors import TransactionError
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.evolution_engine.engine import SchemaEvolutionEngine
from akaal.schema.graph.dependency_graph import ConstraintDependencyGraph
from akaal.schema.transactions.manager import TransactionManager
from akaal.schema.validation.pipeline import ValidationPipeline


class DummyDBContext:
    def __init__(self) -> None:
        self.executed_statements = []

    def execute_statement(self, sql: str) -> None:
        self.executed_statements.append(sql)


def test_transaction_lifecycle_and_rollback_plan():
    tm = TransactionManager()
    tbl = SchemaIdentifier("public", "users")
    ch = AddTable(tbl, columns=[{"name": "id", "type": "INT"}])

    tx = tm.begin_transaction(changes=[ch])
    assert tx.state == TransactionState.PENDING
    assert len(tx.rollback_plan.rollback_statements) == 1
    assert "DROP TABLE" in tx.rollback_plan.rollback_statements[0].sql

    tm.transition_state(tx, TransactionState.VALIDATING)
    tm.transition_state(tx, TransactionState.EXECUTING)
    tm.commit(tx)
    assert tx.state == TransactionState.COMMITTED


def test_constraint_dependency_graph_topological_sort():
    graph = ConstraintDependencyGraph()
    t1 = SchemaIdentifier("public", "parent")
    t2 = SchemaIdentifier("public", "child")

    ch1 = AddTable(t1, columns=[{"name": "id", "type": "INT"}])
    ch2 = AddColumn(t2, column_name="parent_id", data_type="INT")

    graph.add_change(ch1)
    graph.add_change(ch2)

    order = graph.compute_execution_order()
    assert len(order) == 2


def test_schema_evolution_engine_successful_execution():
    engine = SchemaEvolutionEngine()
    db_ctx = DummyDBContext()

    tbl = SchemaIdentifier("public", "products")
    ch = AddTable(tbl, columns=[{"name": "id", "type": "INT"}])

    tx = engine.evolve(changes=[ch], db_context=db_ctx)
    assert tx.state == TransactionState.COMMITTED
    assert len(db_ctx.executed_statements) == 1
    assert "CREATE TABLE" in db_ctx.executed_statements[0]
