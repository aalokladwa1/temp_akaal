"""
tests/unit/engine_cdc/test_m2_snapshot_cdc_overlap_hostile.py
============================================================
Hostile verification of Snapshot + CDC overlap correctness under concurrent I/U/D.
Proves that no source commit disappears between the bulk snapshot and CDC stream,
and that overlapping representation resolves idempotently with:
- 0 duplicate rows
- 0 lost mutations
- 0 resurrected deletes
- 0 stale final images
"""

import os
import sqlite3
import tempfile
import pytest
from typing import Dict, Any, List

from akaalEngine.cdc.apply.coordinator import CDCApplyCoordinator
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType
from akaalEngine.transport.drivers.generic_sql import GenericSQLTargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata


class SQLiteTargetWriter(GenericSQLTargetWriter):
    """Concrete SQLite TargetWriter for in-memory / local test database execution."""

    def __init__(self, db_path: str, migration_id: str = "mig-test"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
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
def target_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    writer = SQLiteTargetWriter(db_path)
    writer.execute_ddl("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            balance REAL NOT NULL,
            version INTEGER NOT NULL DEFAULT 1
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


def test_scenario_a_insert_during_bulk_window(target_db):
    """Scenario A: Row inserted after boundary establishment; bulk snapshot reads it; CDC applies it."""
    writer, db_path = target_db
    coord = CDCApplyCoordinator(target_writer=writer)

    # 1. Bulk transport loads snapshot row (user_id=101)
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "users", "main", 1, 1, 100),
        rows=[{"user_id": 101, "username": "alice", "email": "alice@example.com", "balance": 100.0, "version": 1}],
        column_names=["user_id", "username", "email", "balance", "version"],
    )
    writer.write_batch("users", batch, target_schema="main", pk_columns=["user_id"])

    # 2. CDC event for the same insert drains (overlapping stream event)
    cdc_evt = ChangeEvent(
        event_id="evt-ins-101",
        source_system="SQLITE",
        source_identity="main",
        logical_object="users",
        operation=ChangeOperation.INSERT,
        source_position="pos-101",
        commit_position="pos-101",
        commit_timestamp=1700000001.0,
        capture_timestamp=1700000002.0,
        schema_version="v1.0",
        key_columns=("user_id",),
        key_values={"user_id": 101},
        after_image={"user_id": 101, "username": "alice", "email": "alice@example.com", "balance": 100.0, "version": 1},
    )
    coord.apply_event(cdc_evt, table_name="users", target_schema="main")

    # 3. Assert exact state: 1 row, 0 duplicates
    cursor = writer.conn.execute("SELECT count(*) as cnt, * FROM users WHERE user_id = 101")
    row = cursor.fetchone()
    assert row["cnt"] == 1
    assert row["username"] == "alice"
    assert row["balance"] == 100.0


def test_scenario_b_update_during_bulk_window(target_db):
    """Scenario B: Row exists in bulk snapshot (v1); UPDATE commits during bulk (v2); CDC drains -> v2."""
    writer, db_path = target_db
    coord = CDCApplyCoordinator(target_writer=writer)

    # 1. Bulk writes v1 image
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "users", "main", 1, 1, 100),
        rows=[{"user_id": 201, "username": "bob", "email": "bob@example.com", "balance": 50.0, "version": 1}],
        column_names=["user_id", "username", "email", "balance", "version"],
    )
    writer.write_batch("users", batch, target_schema="main", pk_columns=["user_id"])

    # 2. CDC captures and applies UPDATE to v2
    cdc_evt = ChangeEvent(
        event_id="evt-upd-201",
        source_system="SQLITE",
        source_identity="main",
        logical_object="users",
        operation=ChangeOperation.UPDATE,
        source_position="pos-201",
        commit_position="pos-201",
        commit_timestamp=1700000005.0,
        capture_timestamp=1700000006.0,
        schema_version="v1.0",
        key_columns=("user_id",),
        key_values={"user_id": 201},
        before_image={"user_id": 201, "username": "bob", "email": "bob@example.com", "balance": 50.0, "version": 1},
        after_image={"user_id": 201, "username": "bob_updated", "email": "bob.new@example.com", "balance": 150.0, "version": 2},
    )
    coord.apply_event(cdc_evt, table_name="users", target_schema="main")

    # 3. Assert latest image present, 0 stale images, 0 lost mutations
    cursor = writer.conn.execute("SELECT * FROM users WHERE user_id = 201")
    row = cursor.fetchone()
    assert row is not None
    assert row["username"] == "bob_updated"
    assert row["email"] == "bob.new@example.com"
    assert row["balance"] == 150.0
    assert row["version"] == 2


def test_scenario_c_delete_during_bulk_window(target_db):
    """Scenario C: Row loaded by bulk; DELETE commits during bulk window; CDC drains -> row deleted."""
    writer, db_path = target_db
    coord = CDCApplyCoordinator(target_writer=writer)

    # 1. Bulk snapshot writes row (user_id=301)
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "users", "main", 1, 1, 100),
        rows=[{"user_id": 301, "username": "charlie", "email": "charlie@example.com", "balance": 75.0, "version": 1}],
        column_names=["user_id", "username", "email", "balance", "version"],
    )
    writer.write_batch("users", batch, target_schema="main", pk_columns=["user_id"])

    # 2. CDC applies DELETE mutation
    cdc_evt = ChangeEvent(
        event_id="evt-del-301",
        source_system="SQLITE",
        source_identity="main",
        logical_object="users",
        operation=ChangeOperation.DELETE,
        source_position="pos-301",
        commit_position="pos-301",
        commit_timestamp=1700000010.0,
        capture_timestamp=1700000011.0,
        schema_version="v1.0",
        key_columns=("user_id",),
        key_values={"user_id": 301},
        before_image={"user_id": 301, "username": "charlie", "email": "charlie@example.com", "balance": 75.0, "version": 1},
        deletion_type=DeletionType.EXPLICIT_DELETE,
    )
    coord.apply_event(cdc_evt, table_name="users", target_schema="main")

    # 3. Assert 0 rows: deleted row is NOT resurrected
    cursor = writer.conn.execute("SELECT count(*) as cnt FROM users WHERE user_id = 301")
    assert cursor.fetchone()["cnt"] == 0


def test_scenario_d_multiple_mutations_convergence(target_db):
    """Scenario D: INSERT -> UPDATE -> UPDATE -> DELETE on key 401 during bulk window."""
    writer, db_path = target_db
    coord = CDCApplyCoordinator(target_writer=writer)

    # Sequence of mutations
    e1 = ChangeEvent("e1", "SQLITE", "main", "users", ChangeOperation.INSERT, "p1", "p1", 1.0, 1.0, "v1", ("user_id",), {"user_id": 401}, after_image={"user_id": 401, "username": "d1", "email": "d1@x.com", "balance": 10.0, "version": 1})
    e2 = ChangeEvent("e2", "SQLITE", "main", "users", ChangeOperation.UPDATE, "p2", "p2", 2.0, 2.0, "v1", ("user_id",), {"user_id": 401}, before_image={"user_id": 401, "username": "d1", "email": "d1@x.com", "balance": 10.0, "version": 1}, after_image={"user_id": 401, "username": "d2", "email": "d2@x.com", "balance": 20.0, "version": 2})
    e3 = ChangeEvent("e3", "SQLITE", "main", "users", ChangeOperation.UPDATE, "p3", "p3", 3.0, 3.0, "v1", ("user_id",), {"user_id": 401}, before_image={"user_id": 401, "username": "d2", "email": "d2@x.com", "balance": 20.0, "version": 2}, after_image={"user_id": 401, "username": "d3", "email": "d3@x.com", "balance": 30.0, "version": 3})
    e4 = ChangeEvent("e4", "SQLITE", "main", "users", ChangeOperation.DELETE, "p4", "p4", 4.0, 4.0, "v1", ("user_id",), {"user_id": 401}, before_image={"user_id": 401, "username": "d3", "email": "d3@x.com", "balance": 30.0, "version": 3}, deletion_type=DeletionType.EXPLICIT_DELETE)

    # Bulk read happened to catch v2 state during the window
    batch = TransportBatch(
        metadata=TransportBatchMetadata("b1", "p0", "users", "main", 1, 1, 100),
        rows=[{"user_id": 401, "username": "d2", "email": "d2@x.com", "balance": 20.0, "version": 2}],
        column_names=["user_id", "username", "email", "balance", "version"],
    )
    writer.write_batch("users", batch, target_schema="main", pk_columns=["user_id"])

    # CDC applies the complete stream (e1..e4)
    for evt in [e1, e2, e3, e4]:
        coord.apply_event(evt, table_name="users", target_schema="main")

    # Target state must reflect final DELETE: 0 rows
    cursor = writer.conn.execute("SELECT count(*) as cnt FROM users WHERE user_id = 401")
    assert cursor.fetchone()["cnt"] == 0


def test_scenario_e_boundary_edge_mutation(target_db):
    """Scenario E: Mutation committed immediately at boundary position P0."""
    writer, db_path = target_db
    coord = CDCApplyCoordinator(target_writer=writer)

    # Row 501 inserted at boundary P0
    e0 = ChangeEvent("e0", "SQLITE", "main", "users", ChangeOperation.INSERT, "P0", "P0", 0.0, 0.0, "v1", ("user_id",), {"user_id": 501}, after_image={"user_id": 501, "username": "eve", "email": "eve@x.com", "balance": 500.0, "version": 1})
    coord.apply_event(e0, table_name="users", target_schema="main")

    cursor = writer.conn.execute("SELECT count(*) as cnt, balance FROM users WHERE user_id = 501")
    row = cursor.fetchone()
    assert row["cnt"] == 1
    assert row["balance"] == 500.0
