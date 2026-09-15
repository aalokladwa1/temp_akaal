"""M2 correction: real DAG-dispatch integration test for Bulk+CDC mode.

Proves the protected bulk/CDC consistency boundary: `_handle_cdc_boundary`
establishes the real CDC session (the same `akaal.cdc.*` machinery M3 uses)
BEFORE bulk transport runs; deterministic changes representing concurrent
source mutations during the bulk window are then captured via the
authorized test-only CDC-source seam and applied by `_handle_cdc_apply`
AFTER bulk completes. Final target state must reflect both the bulk
snapshot and the CDC-captured changes, with no loss and no duplication --
against a real on-disk SQLite target, not mocked.
"""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import uuid

import pytest

from akaal.engine.facade import AkaalSuperEngine
from akaal.core.state.state_store import CentralStateStore

_RUN_SUFFIX = uuid.uuid4().hex[:8]


def _sqlite_params(path):
    return {"system_type": "SQLITE", "database_name": path}


def _rows(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        return {r["id"]: dict(r) for r in conn.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()}
    finally:
        conn.close()


@pytest.fixture
def m2_dbs(tmp_path):
    src_path = str(tmp_path / "m2_source.sqlite")
    tgt_path = str(tmp_path / "m2_target.sqlite")
    conn = sqlite3.connect(src_path)
    conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, balance INTEGER)")
    # Pre-boundary rows: present in the bulk snapshot.
    conn.executemany("INSERT INTO accounts VALUES (?,?,?)", [
        (1, "Alice", 100),
        (2, "Bob", 200),
        (3, "Carol", 300),
    ])
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tgt_path)
    conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, balance INTEGER)")
    conn.commit()
    conn.close()
    return src_path, tgt_path


@pytest.fixture
def cdc_wal_dir():
    d = tempfile.mkdtemp(prefix="akaal_m2_dag_cdc_wal_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


M2_STAGES = [
    "Discovery & Catalog Fencing",
    "DAG Topological Dependency Sorting & Schema Routing",
    "Consistent Change Boundary Token Capture",
    "Target Schema Structure Deployment",
    "CDC Change Capture Initialization",
    "Parallel Stream Data Transport",
    "CDC Stream Apply & Continuous Catchup",
    "SHA-256 Digital Trust Seal",
]


def _run_m2(workflow_id, src_path, tgt_path, cdc_wal_dir, transactions):
    eng = AkaalSuperEngine()
    spec_dict = {
        "execution_mode": "M2",
        "physical_spec": {"kind": "M2"},
        "physical_validation_context": {"kind": "reconciliation"},
        "selected_scope": {"objects": [
            {"object_name": "accounts", "target_object_name": "accounts", "object_type": "Table"},
        ]},
        "cdc_test_source_transactions": transactions,
        "cdc_wal_dir": cdc_wal_dir,
    }
    dag_dict = {"dag_stages": [{"stage": i + 1, "name": n} for i, n in enumerate(M2_STAGES)]}
    eng._record_test_governance_approval(workflow_id, spec_dict, dag_dict)
    result = eng.execute_migration(
        workflow_id, spec_dict, dag_dict,
        source_params=_sqlite_params(src_path), target_params=_sqlite_params(tgt_path),
        is_physical=True, is_synthetic_test=False,
    )
    exec_record = CentralStateStore().get_state(f"{workflow_id}_plan_execution", category="runtime")
    return result, exec_record


class TestM2BulkCdcConsistencyBoundary:
    def test_m2_i01_bulk_snapshot_plus_concurrent_cdc_changes_both_land_with_no_loss_no_duplication(self, m2_dbs, cdc_wal_dir):
        src, tgt = m2_dbs
        # Deterministic changes representing mutations that happened DURING
        # the bulk copy window (after the boundary token was captured):
        #   - id=4 is a brand-new row inserted mid-bulk (not in the bulk
        #     snapshot at all -- if the boundary/CDC capture were broken,
        #     this row would be silently lost).
        #   - id=2 (Bob) is updated mid-bulk -- final state must reflect
        #     the UPDATE, not the stale bulk-snapshot value.
        #   - id=3 (Carol) is deleted mid-bulk -- final state must NOT
        #     contain Carol, even though bulk itself would have copied her.
        transactions = [
            {"tx_id": "cdc-1", "commit_timestamp": "2024-01-01T00:00:01+00:00", "events": [
                {"table": "accounts", "operation": "INSERT", "after": {"id": 4, "name": "Dave", "balance": 400}},
            ]},
            {"tx_id": "cdc-2", "commit_timestamp": "2024-01-01T00:00:02+00:00", "events": [
                {"table": "accounts", "operation": "UPDATE",
                 "before": {"id": 2, "name": "Bob", "balance": 200},
                 "after": {"id": 2, "name": "Bob", "balance": 250}},
            ]},
            {"tx_id": "cdc-3", "commit_timestamp": "2024-01-01T00:00:03+00:00", "events": [
                {"table": "accounts", "operation": "DELETE", "before": {"id": 3, "name": "Carol", "balance": 300}},
            ]},
        ]
        result, exec_record = _run_m2(f"wf-m2-dag-i01-{_RUN_SUFFIX}", src, tgt, cdc_wal_dir, transactions)
        assert exec_record["success"] is True, exec_record

        boundary_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Consistent Change Boundary Token Capture")
        assert boundary_stage["details"]["boundary_captured"] is True

        transport_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Parallel Stream Data Transport")
        assert transport_stage["details"]["rows_written"] == 3  # bulk snapshot: Alice, Bob(stale), Carol

        apply_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "CDC Stream Apply & Continuous Catchup")
        assert apply_stage["details"]["transactions_applied"] == 3

        final = _rows(tgt, "accounts")
        # No loss: Dave (mid-bulk insert) present.
        assert final[4] == {"id": 4, "name": "Dave", "balance": 400}
        # Correct final value: Bob's UPDATE applied after the stale bulk copy.
        assert final[2] == {"id": 2, "name": "Bob", "balance": 250}
        # No duplication of a deleted row: Carol removed despite bulk having copied her.
        assert 3 not in final
        assert final[1] == {"id": 1, "name": "Alice", "balance": 100}
        assert len(final) == 3  # Alice, Bob, Dave -- Carol excluded

    def test_m2_i02_zero_cdc_changes_bulk_only_result_is_exact_bulk_snapshot(self, m2_dbs, cdc_wal_dir):
        """Negative/control case: with NO concurrent CDC changes, M2's final
        state must equal a plain bulk copy exactly -- proving the CDC path
        does not fabricate or alter rows it was never given."""
        src, tgt = m2_dbs
        result, exec_record = _run_m2(f"wf-m2-dag-i02-{_RUN_SUFFIX}", src, tgt, cdc_wal_dir, [])
        assert exec_record["success"] is True, exec_record
        final = _rows(tgt, "accounts")
        assert final == {
            1: {"id": 1, "name": "Alice", "balance": 100},
            2: {"id": 2, "name": "Bob", "balance": 200},
            3: {"id": 3, "name": "Carol", "balance": 300},
        }

    def test_m2_i03_illegal_incremental_poll_stage_is_fenced(self, m2_dbs, cdc_wal_dir):
        """Structural proof that M2 is legitimately allowed cdc_boundary +
        transport + cdc_apply together (unlike M3, which forbids transport),
        while an M4-only responsibility (incremental_poll) is still refused."""
        src, tgt = m2_dbs
        eng = AkaalSuperEngine()
        wf = f"wf-m2-dag-i03b-{_RUN_SUFFIX}"
        spec_dict = {
            "execution_mode": "M2",
            "physical_spec": {"kind": "M2"},
            "physical_validation_context": {"kind": "reconciliation"},
            "selected_scope": {"objects": [{"object_name": "accounts", "target_object_name": "accounts", "object_type": "Table"}]},
            "cdc_test_source_transactions": [],
            "cdc_wal_dir": cdc_wal_dir,
        }
        stages = M2_STAGES[:2] + ["Incremental Watermark Query & Batch Apply"] + M2_STAGES[2:]
        dag_dict = {"dag_stages": [{"stage": i + 1, "name": n} for i, n in enumerate(stages)]}
        eng._record_test_governance_approval(wf, spec_dict, dag_dict)
        with pytest.raises(RuntimeError):
            eng.execute_migration(wf, spec_dict, dag_dict, source_params=_sqlite_params(src),
                                   target_params=_sqlite_params(tgt), is_physical=True, is_synthetic_test=False)
        exec_record = CentralStateStore().get_state(f"{wf}_plan_execution", category="runtime")
        poll_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Incremental Watermark Query & Batch Apply")
        assert poll_stage["success"] is False
        assert "MODE_FENCE_VIOLATION" in poll_stage["errors"][0]
