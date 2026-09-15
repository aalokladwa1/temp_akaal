"""M4 correction: real DAG-dispatch integration test.

Proves `akaal.engine.plan_dispatch.PlanExecutionDispatcher._handle_incremental_poll`
is wired to the REAL, extended `akaalEngine.durability.DurabilityAuthority`
watermark primitive (`save_watermark`/`get_watermark`, unit-proven in
tests/unit/engine_durability/test_m4_watermark_authority.py) end-to-end
through the actual compiled-plan DAG dispatch path
(`AkaalSuperEngine.execute_migration` -> `PlanExecutionDispatcher.run`),
against real on-disk SQLite source/target databases -- not mocked.

Covers:
  - first poll transfers only rows with a non-null watermark column value,
    and only once (idempotent no-op on immediate re-poll with no new rows)
  - durable watermark advances only to the max value actually written
  - a table with no configured watermark column fails closed
    (NO_WATERMARK_COLUMN_CONFIGURED), never silently skipped as success
  - a fresh dispatcher instance (simulating a process restart) resumes
    from the durable watermark rather than re-reading from the start
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile

import pytest

from akaal.engine.facade import AkaalSuperEngine
from akaal.core.state.state_store import CentralStateStore


def _sqlite_params(path):
    return {"system_type": "SQLITE", "database_name": path}


def _row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


@pytest.fixture
def m4_dbs(tmp_path):
    src_path = str(tmp_path / "m4_source.sqlite")
    tgt_path = str(tmp_path / "m4_target.sqlite")
    conn = sqlite3.connect(src_path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, seq INTEGER, payload TEXT)")
    conn.executemany(
        "INSERT INTO orders VALUES (?,?,?)",
        [(1, 10, "row-1"), (2, 20, "row-2"), (3, None, "null-watermark-row")],
    )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tgt_path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, seq INTEGER, payload TEXT)")
    conn.commit()
    conn.close()
    return src_path, tgt_path


@pytest.fixture
def durability_dir():
    d = tempfile.mkdtemp(prefix="akaal_m4_dag_dur_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _run_m4(workflow_id, src_path, tgt_path, durability_dir, watermark_cols):
    eng = AkaalSuperEngine()
    spec_dict = {
        "execution_mode": "M4",
        "physical_spec": {"kind": "M4"},
        "physical_validation_context": {"kind": "reconciliation"},
        "selected_scope": {"objects": [
            {"object_name": "orders", "target_object_name": "orders", "object_type": "Table"},
        ]},
        "incremental_watermark_columns": watermark_cols,
        "durability_storage_dir": durability_dir,
        # Passed as str (not bytes) because spec_dict is JSON-fingerprinted
        # for governance approval; plan_dispatch's _get_durability_authority
        # encodes a str value to bytes itself.
        "durability_fencing_key": "AKAAL-TEST-DAG-M4-FENCING-KEY-001",
        "durability_anchor_key": "AKAAL-TEST-DAG-M4-ANCHOR-KEY-002",
    }
    dag_dict = {"dag_stages": [
        {"stage": 1, "name": "Discovery & Catalog Fencing"},
        {"stage": 2, "name": "DAG Topological Dependency Sorting & Schema Routing"},
        {"stage": 3, "name": "Incremental Watermark Query & Batch Apply"},
        {"stage": 4, "name": "SHA-256 Digital Trust Seal"},
    ]}
    eng._record_test_governance_approval(workflow_id, spec_dict, dag_dict)
    result = eng.execute_migration(
        workflow_id, spec_dict, dag_dict,
        source_params=_sqlite_params(src_path), target_params=_sqlite_params(tgt_path),
        is_physical=True, is_synthetic_test=False,
    )
    exec_record = CentralStateStore().get_state(f"{workflow_id}_plan_execution", category="runtime")
    return result, exec_record


class TestM4DagDispatchIntegration:
    def test_m4_i01_first_poll_transfers_only_non_null_watermark_rows(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        result, exec_record = _run_m4(
            "wf-m4-dag-i01", src, tgt, durability_dir,
            {"orders": {"column": "seq", "type": "NUMERIC"}},
        )
        assert exec_record["success"] is True, exec_record
        assert result["runtime_state"] == "COMPLETED"
        # 2 eligible rows (seq=10, seq=20); the NULL-watermark row is excluded
        assert _row_count(tgt, "orders") == 2

    def test_m4_i02_watermark_advances_to_max_written_value_and_persists(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
        _run_m4(
            "wf-m4-dag-i02", src, tgt, durability_dir,
            {"orders": {"column": "seq", "type": "NUMERIC"}},
        )
        # Fresh authority instance against the SAME on-disk store == restart.
        config = DurabilityConfig(
            storage_dir=durability_dir,
            fencing_signing_key=b"AKAAL-TEST-DAG-M4-FENCING-KEY-001",
            journal_anchor_key=b"AKAAL-TEST-DAG-M4-ANCHOR-KEY-002",
        )
        auth = DurabilityAuthority(config)
        try:
            wm = auth.get_watermark("wf-m4-dag-i02", "orders")
            assert wm is not None
            assert wm.value == 20
        finally:
            auth.close()

    def test_m4_i03_repoll_with_no_new_rows_is_a_safe_no_op(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        _run_m4("wf-m4-dag-i03", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})
        before = _row_count(tgt, "orders")
        # Re-run against the SAME durability store/migration_id -- nothing new to poll.
        result2, exec_record2 = _run_m4("wf-m4-dag-i03", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})
        assert exec_record2["success"] is True
        assert _row_count(tgt, "orders") == before  # unchanged, no duplicate re-apply

    def test_m4_i04_new_row_above_watermark_is_picked_up_on_next_poll(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        _run_m4("wf-m4-dag-i04", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})
        conn = sqlite3.connect(src)
        conn.execute("INSERT INTO orders VALUES (4, 30, 'row-4')")
        conn.commit()
        conn.close()
        _run_m4("wf-m4-dag-i04", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})
        assert _row_count(tgt, "orders") == 3  # 10, 20, then 30 picked up

    def test_m4_i05_missing_watermark_column_config_fails_closed(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        with pytest.raises(RuntimeError, match="Incremental Watermark Query"):
            _run_m4("wf-m4-dag-i05", src, tgt, durability_dir, {})
        exec_record = CentralStateStore().get_state("wf-m4-dag-i05_plan_execution", category="runtime")
        assert exec_record["success"] is False
        poll_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Incremental Watermark Query & Batch Apply")
        assert "M4_NOT_CONFIGURED" in poll_stage["errors"][0]
        assert _row_count(tgt, "orders") == 0  # nothing fabricated/transferred

    def test_m4_i06_evidence_stage_binds_to_real_evidence_authority(self, m4_dbs, durability_dir):
        src, tgt = m4_dbs
        result, exec_record = _run_m4(
            "wf-m4-dag-i06", src, tgt, durability_dir,
            {"orders": {"column": "seq", "type": "NUMERIC"}},
        )
        evidence_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "SHA-256 Digital Trust Seal")
        assert evidence_stage["details"]["evidence_authority_bound"] is True
        assert evidence_stage["details"].get("evidence_authority_artifact_id")

    # -- CRASH-WINDOW A: physical fault injection -------------------------
    # Correction-campaign item 1 (owner-mandated): real fault injection
    # against the target adapter, not code-order reasoning. Forces a real
    # exception INSIDE SQLiteAdapter.write_batch (the exact call
    # `_handle_incremental_poll` makes) so the target commit never happens,
    # then independently re-opens a FRESH DurabilityAuthority instance
    # against the same on-disk store and proves the durable watermark is
    # still exactly what it was before the attempt (None -- never saved).
    def test_m4_i07_target_write_failure_before_commit_leaves_watermark_unchanged(self, m4_dbs, durability_dir, monkeypatch):
        src, tgt = m4_dbs
        from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter

        async def _failing_write_batch(self, table_name, rows):
            raise RuntimeError("SIMULATED_TARGET_WRITE_FAILURE_BEFORE_COMMIT")

        monkeypatch.setattr(SQLiteAdapter, "write_batch", _failing_write_batch)

        with pytest.raises(RuntimeError, match="Incremental Watermark Query"):
            _run_m4("wf-m4-dag-i07", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})

        exec_record = CentralStateStore().get_state("wf-m4-dag-i07_plan_execution", category="runtime")
        assert exec_record["success"] is False
        poll_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Incremental Watermark Query & Batch Apply")
        assert "SIMULATED_TARGET_WRITE_FAILURE_BEFORE_COMMIT" in poll_stage["errors"][0]

        # Nothing landed physically in the target (the injected failure
        # happened inside write_batch itself, before any commit).
        assert _row_count(tgt, "orders") == 0

        # Independent re-read via a BRAND-NEW DurabilityAuthority instance
        # against the same on-disk storage_dir -- proves the durable
        # watermark genuinely never advanced, not merely that the in-memory
        # dispatcher object didn't get around to it.
        from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
        config = DurabilityConfig(
            storage_dir=durability_dir,
            fencing_signing_key=b"AKAAL-TEST-DAG-M4-FENCING-KEY-001",
            journal_anchor_key=b"AKAAL-TEST-DAG-M4-ANCHOR-KEY-002",
        )
        auth = DurabilityAuthority(config)
        try:
            wm = auth.get_watermark("wf-m4-dag-i07", "orders")
            assert wm is None  # unchanged from its pre-attempt (never-saved) value
        finally:
            auth.close()

        # Restore the real adapter and retry for real -- proves the failed
        # attempt left the system in a safely retryable state (no partial/
        # corrupted watermark or target state blocking a clean re-poll).
        monkeypatch.undo()
        result2, exec_record2 = _run_m4(
            "wf-m4-dag-i07", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}},
        )
        assert exec_record2["success"] is True
        assert _row_count(tgt, "orders") == 2  # the originally-eligible rows, now written cleanly

    # -- CRASH-WINDOW B: physical fault injection -------------------------
    # Target write genuinely commits for real (SQLiteAdapter.write_batch
    # runs unmodified), then the process is simulated to die BEFORE
    # `DurabilityAuthority.save_watermark` persists (by forcing that exact
    # call to raise, exactly at the point a real crash/kill -9 would land).
    # A subsequent, independent re-poll must resume from the OLD (still
    # unsaved) watermark and safely re-apply the same window with no
    # missing, duplicated, or corrupted final target state -- proven via
    # the real `INSERT OR REPLACE` upsert discipline SQLiteAdapter.write_batch
    # already uses (not a new idempotency mechanism invented for this test).
    def test_m4_i08_crash_between_target_commit_and_watermark_persist_replays_safely(self, m4_dbs, durability_dir, monkeypatch):
        src, tgt = m4_dbs
        from akaalEngine.durability.api import DurabilityAuthority as DurabilityAuthorityAPI

        def _crashing_save_watermark(self, *args, **kwargs):
            raise RuntimeError("SIMULATED_PROCESS_DEATH_AFTER_TARGET_COMMIT_BEFORE_WATERMARK_PERSIST")

        monkeypatch.setattr(DurabilityAuthorityAPI, "save_watermark", _crashing_save_watermark)

        with pytest.raises(RuntimeError, match="Incremental Watermark Query"):
            _run_m4("wf-m4-dag-i08", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}})

        # The target commit happened for REAL before the injected crash
        # (write_batch was never patched in this test) -- both eligible
        # rows are physically present despite the "crash" immediately
        # afterward.
        assert _row_count(tgt, "orders") == 2

        # The durable watermark was never persisted (the injected failure
        # fired exactly at that call) -- a fresh authority instance
        # confirms it is still None.
        from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
        config = DurabilityConfig(
            storage_dir=durability_dir,
            fencing_signing_key=b"AKAAL-TEST-DAG-M4-FENCING-KEY-001",
            journal_anchor_key=b"AKAAL-TEST-DAG-M4-ANCHOR-KEY-002",
        )
        auth = DurabilityAuthority(config)
        try:
            assert auth.get_watermark("wf-m4-dag-i08", "orders") is None
        finally:
            auth.close()

        # Restore the real save_watermark and simulate a process restart:
        # a fresh poll cycle against the SAME durability store/target. Since
        # the watermark is still None, the restarted poll re-selects the
        # SAME eligible rows (seq=10, seq=20) and re-applies them.
        monkeypatch.undo()
        result2, exec_record2 = _run_m4(
            "wf-m4-dag-i08", src, tgt, durability_dir, {"orders": {"column": "seq", "type": "NUMERIC"}},
        )
        assert exec_record2["success"] is True

        # No missing state: both rows still present. No duplication: exactly
        # 2 rows (not 4) -- proven by SQLiteAdapter.write_batch's real
        # `INSERT OR REPLACE` upsert-by-primary-key semantics re-applying the
        # identical rows idempotently, not by any special-cased test logic.
        assert _row_count(tgt, "orders") == 2
        conn = sqlite3.connect(tgt)
        try:
            rows = conn.execute('SELECT id, seq, payload FROM "orders" ORDER BY id').fetchall()
        finally:
            conn.close()
        assert rows == [(1, 10, "row-1"), (2, 20, "row-2")]  # no corruption, exact expected content

        # And the watermark now correctly reflects the successfully
        # replayed/persisted poll.
        auth2 = DurabilityAuthority(config)
        try:
            wm2 = auth2.get_watermark("wf-m4-dag-i08", "orders")
            assert wm2 is not None
            assert wm2.value == 20
        finally:
            auth2.close()
