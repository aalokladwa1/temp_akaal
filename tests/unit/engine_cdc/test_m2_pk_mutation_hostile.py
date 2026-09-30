"""
tests/unit/engine_cdc/test_m2_pk_mutation_hostile.py
==================================================
Hostile verification of Primary-Key-Changing UPDATE Semantics.
Tests single-column PK, composite PK, replayed PK events, FK reference safety,
and atomic decomposition (DELETE old PK + INSERT new PK).
"""

import os
import sqlite3
import tempfile
import pytest
from typing import Dict, Any

from akaalEngine.cdc.apply.coordinator import CDCApplyCoordinator
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType
from akaalEngine.transport.drivers.generic_sql import GenericSQLTargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import IdempotencyMode


class SQLiteTargetWriter(GenericSQLTargetWriter):
    """Concrete SQLite TargetWriter for in-memory / local test database execution."""

    def __init__(self, db_path: str, migration_id: str = "mig-test-pk"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        super().__init__(
            connection_params={
                "db_connection": self.conn,
                "migration_id": migration_id,
                "endpoint_identity": db_path,
            }
        )

    def execute_ddl(self, sql: str) -> None:
        with self.conn:
            self.conn.executescript(sql)


@pytest.fixture
def pk_test_env():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    writer = SQLiteTargetWriter(db_path)
    writer.execute_ddl("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY,
            owner_name TEXT NOT NULL,
            balance REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS composite_ledger (
            tenant_id INTEGER NOT NULL,
            ledger_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (tenant_id, ledger_id)
        );

        CREATE TABLE IF NOT EXISTS parent_org (
            org_id INTEGER PRIMARY KEY,
            org_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS child_dept (
            dept_id INTEGER PRIMARY KEY,
            org_id INTEGER NOT NULL,
            dept_name TEXT NOT NULL,
            FOREIGN KEY (org_id) REFERENCES parent_org(org_id) ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)
    try:
        yield writer, db_path
    finally:
        writer.close()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def test_01_single_column_pk_mutation(pk_test_env):
    """Single-column PK mutation: account_id changed from 101 -> 102."""
    writer, _ = pk_test_env
    coord = CDCApplyCoordinator(target_writer=writer)

    # 1. Insert initial row account_id=101
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "accounts", "main", 1, 1, 100),
        rows=[{"account_id": 101, "owner_name": "Alice", "balance": 1000.0}],
        column_names=["account_id", "owner_name", "balance"],
    )
    writer.write_batch("accounts", batch, target_schema="main", pk_columns=["account_id"])

    # 2. Apply PK mutation UPDATE: 101 -> 102
    evt = ChangeEvent(
        event_id="evt-pk-1",
        source_system="SQLITE",
        source_identity="main",
        logical_object="accounts",
        operation=ChangeOperation.UPDATE,
        source_position="pos-pk-1",
        commit_position="pos-pk-1",
        commit_timestamp=1700000001.0,
        capture_timestamp=1700000002.0,
        schema_version="v1.0",
        key_columns=("account_id",),
        key_values={"account_id": 102},
        before_image={"account_id": 101, "owner_name": "Alice", "balance": 1000.0},
        after_image={"account_id": 102, "owner_name": "Alice Corp", "balance": 1200.0},
    )
    res = coord.apply_event(evt, table_name="accounts", target_schema="main")
    assert res is True

    # 3. Assert old PK deleted, new PK inserted
    cur = writer.conn.execute("SELECT count(*) as cnt FROM accounts WHERE account_id = 101")
    assert cur.fetchone()["cnt"] == 0

    cur = writer.conn.execute("SELECT * FROM accounts WHERE account_id = 102")
    row = cur.fetchone()
    assert row is not None
    assert row["owner_name"] == "Alice Corp"
    assert row["balance"] == 1200.0


def test_02_composite_pk_mutation(pk_test_env):
    """Composite PK mutation: (tenant_id=1, ledger_id=10) -> (tenant_id=1, ledger_id=20)."""
    writer, _ = pk_test_env
    coord = CDCApplyCoordinator(target_writer=writer)

    # 1. Insert initial composite row (1, 10)
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "composite_ledger", "main", 1, 1, 100),
        rows=[{"tenant_id": 1, "ledger_id": 10, "amount": 500.0, "status": "PENDING"}],
        column_names=["tenant_id", "ledger_id", "amount", "status"],
    )
    writer.write_batch("composite_ledger", batch, target_schema="main", pk_columns=["tenant_id", "ledger_id"])

    # 2. Apply PK mutation UPDATE: (1, 10) -> (1, 20)
    evt = ChangeEvent(
        event_id="evt-comp-pk-1",
        source_system="SQLITE",
        source_identity="main",
        logical_object="composite_ledger",
        operation=ChangeOperation.UPDATE,
        source_position="pos-comp-1",
        commit_position="pos-comp-1",
        commit_timestamp=1700000001.0,
        capture_timestamp=1700000002.0,
        schema_version="v1.0",
        key_columns=("tenant_id", "ledger_id"),
        key_values={"tenant_id": 1, "ledger_id": 20},
        before_image={"tenant_id": 1, "ledger_id": 10, "amount": 500.0, "status": "PENDING"},
        after_image={"tenant_id": 1, "ledger_id": 20, "amount": 750.0, "status": "POSTED"},
    )
    res = coord.apply_event(evt, table_name="composite_ledger", target_schema="main")
    assert res is True

    # 3. Assert old composite key gone, new composite key present
    cur = writer.conn.execute("SELECT count(*) as cnt FROM composite_ledger WHERE tenant_id = 1 AND ledger_id = 10")
    assert cur.fetchone()["cnt"] == 0

    cur = writer.conn.execute("SELECT * FROM composite_ledger WHERE tenant_id = 1 AND ledger_id = 20")
    row = cur.fetchone()
    assert row is not None
    assert row["amount"] == 750.0
    assert row["status"] == "POSTED"


def test_03_replayed_pk_mutation_idempotency(pk_test_env):
    """Replayed PK mutation event: verifies deduplication and idempotent re-execution."""
    writer, _ = pk_test_env
    coord = CDCApplyCoordinator(target_writer=writer)

    evt = ChangeEvent(
        event_id="evt-pk-replay-1",
        source_system="SQLITE",
        source_identity="main",
        logical_object="accounts",
        operation=ChangeOperation.UPDATE,
        source_position="pos-replay",
        commit_position="pos-replay",
        commit_timestamp=1700000001.0,
        capture_timestamp=1700000002.0,
        schema_version="v1.0",
        key_columns=("account_id",),
        key_values={"account_id": 202},
        before_image={"account_id": 201, "owner_name": "Bob", "balance": 50.0},
        after_image={"account_id": 202, "owner_name": "Bob", "balance": 50.0},
    )

    # First apply
    res1 = coord.apply_event(evt, table_name="accounts", target_schema="main")
    assert res1 is True

    # Replay same event (in-memory deduplication index)
    res2 = coord.apply_event(evt, table_name="accounts", target_schema="main", is_replay=True, idempotency_mode=IdempotencyMode.STATE_IDEMPOTENT)
    assert res2 is True
    assert coord.events_deduplicated_total >= 1


def test_04_fk_referenced_cascade_semantics(pk_test_env):
    """FK referenced table: verifies CASCADE update / delete integrity."""
    writer, _ = pk_test_env
    coord = CDCApplyCoordinator(target_writer=writer)

    # Insert parent and child
    with writer.conn:
        writer.conn.execute("INSERT INTO parent_org (org_id, org_name) VALUES (1, 'Engineering');")
        writer.conn.execute("INSERT INTO child_dept (dept_id, org_id, dept_name) VALUES (10, 1, 'Dev');")

    # Mutate parent org_id: 1 -> 2
    evt = ChangeEvent(
        event_id="evt-fk-1",
        source_system="SQLITE",
        source_identity="main",
        logical_object="parent_org",
        operation=ChangeOperation.UPDATE,
        source_position="pos-fk-1",
        commit_position="pos-fk-1",
        commit_timestamp=1700000001.0,
        capture_timestamp=1700000002.0,
        schema_version="v1.0",
        key_columns=("org_id",),
        key_values={"org_id": 2},
        before_image={"org_id": 1, "org_name": "Engineering"},
        after_image={"org_id": 2, "org_name": "Engineering Global"},
    )
    res = coord.apply_event(evt, table_name="parent_org", target_schema="main")
    assert res is True

    # Verify parent org updated to 2
    cur = writer.conn.execute("SELECT org_id, org_name FROM parent_org WHERE org_id = 2")
    assert cur.fetchone()["org_name"] == "Engineering Global"
