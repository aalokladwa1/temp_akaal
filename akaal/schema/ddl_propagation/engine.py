"""
AKAAL Platform 5 — DDLPlanner & DDLExecutor

Provides DDL planning, statement hashing, idempotent retry policies, and propagation.
"""

from dataclasses import dataclass
import hashlib
import time
from typing import Any, List, Optional

from akaal.schema.domain.changes import DDLStatement
from akaal.schema.domain.errors import ExecutionError
from akaal.schema.ddl_propagation.history import PropagationHistory


class DDLPlanner:
    """Plans DDL statements and computes cryptographic idempotency hashes."""

    @staticmethod
    def compute_statement_hash(stmt: DDLStatement) -> str:
        raw = f"{stmt.target_object}:{stmt.sql.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DDLExecutor:
    """Executes DDL statements with automatic retry backoff and idempotency checks."""

    def __init__(self, history: Optional[PropagationHistory] = None, max_retries: int = 3) -> None:
        self.history = history or PropagationHistory()
        self.max_retries = max_retries

    def execute_statement(self, stmt: DDLStatement, db_context: Any = None) -> bool:
        stmt_hash = DDLPlanner.compute_statement_hash(stmt)

        # Idempotency check: skip if already successfully executed
        if self.history.is_executed(stmt_hash):
            return True

        attempts = 0
        last_error = None

        while attempts <= self.max_retries:
            try:
                if db_context and hasattr(db_context, "execute_statement"):
                    db_context.execute_statement(stmt.sql)

                self.history.record_execution(
                    stmt_hash=stmt_hash,
                    sql=stmt.sql,
                    target_object=stmt.target_object,
                    success=True,
                    retries=attempts,
                )
                return True

            except Exception as e:
                last_error = str(e)
                attempts += 1
                if attempts <= self.max_retries:
                    time.sleep(0.01 * (2 ** (attempts - 1)))  # Exponential backoff

        self.history.record_execution(
            stmt_hash=stmt_hash,
            sql=stmt.sql,
            target_object=stmt.target_object,
            success=False,
            error=last_error,
            retries=attempts - 1,
        )
        raise ExecutionError(
            message=f"DDL execution failed after {self.max_retries} retries for '{stmt.target_object}': {last_error}",
            recovery_recommendation="Verify database lock availability and user permissions."
        )


class DDLPropagationEngine:
    """Online DDL Propagation Engine orchestrating planning and execution."""

    def __init__(self, executor: Optional[DDLExecutor] = None) -> None:
        self.planner = DDLPlanner()
        self.executor = executor or DDLExecutor()

    def propagate(self, ddl_statements: List[DDLStatement], db_context: Any = None) -> bool:
        for stmt in ddl_statements:
            self.executor.execute_statement(stmt, db_context)
        return True
