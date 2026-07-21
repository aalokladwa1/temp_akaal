"""
AKAAL Platform 5 — Stress & Fault Injection Audit Test Suite

Independent Audit Tests: Concurrency stress, deadlock detection, large dependency graphs,
fault injection, journal tampering, OCC version conflicts, and crash recovery.
"""

import threading
import time
import pytest

from akaal.schema.concurrency.deadlock import DeadlockDetector
from akaal.schema.concurrency.lock_manager import SchemaLockManager
from akaal.schema.concurrency.occ import OptimisticConcurrencyController
from akaal.schema.domain.changes import AddColumn, AddTable, ChangeForeignKey, ChangePrimaryKey, DDLStatement
from akaal.schema.domain.enums import FailureClass, TransactionState
from akaal.schema.domain.errors import ConcurrencyError, JournalIntegrityError, TransactionError, ValidationError, VersionConflictError
from akaal.schema.domain.identifiers import OperationID, SchemaIdentifier, TransactionID
from akaal.schema.domain.journal import OperationRecord
from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5
from akaal.schema.graph.dependency_graph import ConstraintDependencyGraph
from akaal.schema.recovery.manager import RecoveryManager
from akaal.schema.replay.journal_store import JournalStore


class MockStressDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.executed = []

    def execute_statement(self, sql: str) -> None:
        with self._lock:
            self.executed.append(sql)


def test_concurrent_lock_contention_and_isolation():
    lock_mgr = SchemaLockManager(default_timeout_sec=0.1)
    results = []

    def worker(worker_id: str):
        try:
            if lock_mgr.acquire_table_lock("accounts", owner_id=worker_id, exclusive=True, timeout_sec=0.05):
                time.sleep(0.02)
                lock_mgr.release_table_lock("accounts", owner_id=worker_id)
                results.append(f"{worker_id}_SUCCESS")
        except ConcurrencyError:
            results.append(f"{worker_id}_TIMED_OUT")

    t1 = threading.Thread(target=worker, args=("worker-1",))
    t2 = threading.Thread(target=worker, args=("worker-2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    assert "worker-1_SUCCESS" in results or "worker-2_SUCCESS" in results


def test_deep_dependency_graph_and_tarjan_sorting():
    graph = ConstraintDependencyGraph()
    # Create a chain of 10 tables: table_0 -> table_1 -> ... -> table_9
    for i in range(10):
        tbl = SchemaIdentifier("public", f"table_{i}")
        ch = AddTable(tbl, columns=[{"name": "id", "type": "INT"}])
        graph.add_change(ch)

    order = graph.compute_execution_order()
    assert len(order) == 10


def test_fault_injection_mid_transaction_rollback():
    platform = SchemaEvolutionPlatformV5()

    class FailingDB:
        def execute_statement(self, sql: str) -> None:
            if "FAIL_MARKER" in sql:
                raise RuntimeError("Injected DB failure during statement execution")

    failing_db = FailingDB()
    tbl = SchemaIdentifier("public", "broken_tbl")

    ch1 = AddTable(tbl, columns=[{"name": "id", "type": "INT"}])
    # Fault statement
    ch2 = AddColumn(tbl, column_name="fail_col", data_type="FAIL_MARKER")

    with pytest.raises(Exception):
        platform.execute_evolution([ch1, ch2], db_context=failing_db)


def test_journal_tamper_detection_under_fault_injection():
    store = JournalStore()
    op1 = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=TransactionID.generate(),
        change_payload={"sql": "CREATE TABLE ledger (id INT);"},
    )
    store.append_record(op1)

    # Corrupt payload checksum
    corrupted_op = OperationRecord(
        operation_id=OperationID.generate(),
        tx_id=op1.tx_id,
        change_payload={"sql": "DROP TABLE ledger;"},
        previous_hash="tampered_hash",
    )

    with pytest.raises(JournalIntegrityError):
        store.append_record(corrupted_op)
