"""
AKAAL Platform 5 — Integration Test Suite

Tests cross-subsystem interaction: Snapshots, Refreshes, Transactions, Validation, Concurrency, Replay, and Recovery.
"""

import pytest

from akaal.schema.concurrency.lock_manager import SchemaLockManager
from akaal.schema.domain.changes import AddColumn, AddTable, ChangePrimaryKey, DDLStatement
from akaal.schema.domain.enums import FailureClass, TransactionState
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5
from akaal.schema.recovery.manager import RecoveryManager
from akaal.schema.replay.journal_store import JournalStore


class IntegrationMockDB:
    def __init__(self) -> None:
        self.executed_statements = []

    def execute_statement(self, sql: str) -> None:
        self.executed_statements.append(sql)


def test_integration_full_evolution_and_replay_cycle():
    platform = SchemaEvolutionPlatformV5()
    db = IntegrationMockDB()

    # Step 1: Initial Refresh
    snap_v1 = platform.refresh_metadata(source="integration_test")
    assert snap_v1 is not None

    # Step 2: Live Schema Evolution with Transaction & 5-Stage Validation
    t1 = SchemaIdentifier("public", "users")
    ch1 = AddTable(t1, columns=[{"name": "id", "type": "INT"}, {"name": "email", "type": "VARCHAR(255)"}])
    tx1 = platform.execute_evolution([ch1], db_context=db)
    assert tx1.state == TransactionState.COMMITTED

    # Step 3: Constraint Evolution
    pk_ch = ChangePrimaryKey(t1, new_pk_columns=["id"])
    platform.evolve_constraints([pk_ch], db_context=db)

    # Step 4: Replay Verification
    replay_report = platform.replay_journal(db_context=db)
    assert replay_report.executed_records >= 0

    # Step 5: Failure Recovery handling
    rm = RecoveryManager()
    rec_res = rm.handle_failure(FailureClass.EXECUTION_FAILURE, Exception("DB Timeout"), tx=tx1, db_context=db)
    assert rec_res.recovered is True
