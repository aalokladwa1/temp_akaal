"""
Unit tests for Feature 6 — Online DDL Propagation.
"""

import pytest

from akaal.schema.ddl_propagation.engine import DDLPropagationEngine
from akaal.schema.ddl_propagation.executor import DDLExecutor
from akaal.schema.ddl_propagation.history import PropagationHistory
from akaal.schema.ddl_propagation.planner import DDLPlanner
from akaal.schema.domain.changes import DDLStatement
from akaal.schema.domain.errors import ExecutionError


class FlakyDBContext:
    def __init__(self, fail_count: int = 0) -> None:
        self.fail_count = fail_count
        self.attempts = 0
        self.executed = []

    def execute_statement(self, sql: str) -> None:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise RuntimeError("Database connection timeout")
        self.executed.append(sql)


def test_ddl_planner_statement_hash():
    stmt1 = DDLStatement(sql="CREATE TABLE users (id INT);", target_object="users")
    stmt2 = DDLStatement(sql="create table users (id int);", target_object="users")
    h1 = DDLPlanner.compute_statement_hash(stmt1)
    h2 = DDLPlanner.compute_statement_hash(stmt2)
    assert h1 == h2


def test_ddl_executor_idempotency_and_retry():
    hist = PropagationHistory()
    executor = DDLExecutor(history=hist, max_retries=3)
    db = FlakyDBContext(fail_count=2)

    stmt = DDLStatement(sql="ALTER TABLE users ADD COLUMN age INT;", target_object="users")

    res = executor.execute_statement(stmt, db_context=db)
    assert res is True
    assert db.attempts == 3  # 2 fails + 1 success

    # Idempotent second call skips execution
    res2 = executor.execute_statement(stmt, db_context=db)
    assert res2 is True
    assert db.attempts == 3  # Not incremented
