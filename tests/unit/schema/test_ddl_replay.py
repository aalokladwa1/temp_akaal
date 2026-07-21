"""
Unit tests for Feature 8 — DDL Replay & Immutable Operation Journal.
"""

import pytest

from akaal.schema.domain.enums import ReplayStatus
from akaal.schema.domain.errors import JournalIntegrityError
from akaal.schema.domain.identifiers import OperationID, TransactionID
from akaal.schema.domain.journal import OperationRecord
from akaal.schema.replay.engine import DDLReplayEngine
from akaal.schema.replay.journal_store import JournalStore


class DummyDBContext:
    def __init__(self) -> None:
        self.executed = []

    def execute_statement(self, sql: str) -> None:
        self.executed.append(sql)


def test_operation_journal_hash_chaining_and_tampering():
    store = JournalStore()
    op1 = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=TransactionID.generate(),
        change_payload={"sql": "CREATE TABLE t1 (id INT);"},
        previous_hash="0" * 64,
    )
    store.append_record(op1)

    op2 = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=op1.tx_id,
        change_payload={"sql": "ALTER TABLE t1 ADD COLUMN name TEXT;"},
        previous_hash=op1.checksum.hash_value,
    )
    store.append_record(op2)

    assert store.count() == 2

    # Tamper test with invalid previous hash
    bad_op = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=op1.tx_id,
        change_payload={"sql": "DROP TABLE t1;"},
        previous_hash="invalid_hash_value",
    )
    with pytest.raises(JournalIntegrityError):
        store.append_record(bad_op)


def test_ddl_replay_engine_execution_and_checkpointing():
    store = JournalStore()
    op1 = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=TransactionID.generate(),
        change_payload={"sql": "CREATE TABLE orders (id INT);"},
    )
    store.append_record(op1)
    chk1 = store.create_checkpoint()

    op2 = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=op1.tx_id,
        change_payload={"sql": "ALTER TABLE orders ADD COLUMN total DECIMAL;"},
        previous_hash=op1.checksum.hash_value,
    )
    store.append_record(op2)

    db = DummyDBContext()
    engine = DDLReplayEngine(journal_store=store)

    report = engine.replay(start_checkpoint=chk1, db_context=db)
    assert report.executed_records == 1
    assert len(db.executed) == 1
    assert "ALTER TABLE orders" in db.executed[0]
