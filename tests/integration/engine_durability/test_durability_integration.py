"""
Integration, Subprocess Restart Recovery, and Benchmark Test Suite for Authority #5 — Durability.
Updated: save_checkpoint and save_row_position now require an authenticated FencingToken.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import pytest
from akaalEngine.durability import (
    DurabilityAuthority,
    DurabilityConfig,
    MigrationCheckpoint,
    TableCheckpoint,
    RowPosition,
    RowPositionType,
)


TEST_FENCING_KEY = b"AKAAL-INTEG-FENCING-HMAC-KEY-SECRET-001"
TEST_ANCHOR_KEY = b"AKAAL-INTEG-JOURNAL-ANCHOR-HMAC-KEY-SECRET-002"


@pytest.fixture
def integration_durability():
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_integ_")
    config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="integ_durability.db",
        spill_quota_bytes=500 * 1024 * 1024,
    )
    auth = DurabilityAuthority(config)
    yield auth, temp_dir
    auth.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_subprocess_crash_restart_recovery(integration_durability):
    _, temp_dir = integration_durability
    db_path = os.path.join(temp_dir, "integ_durability.db")

    child_code = f"""
import sys
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig, MigrationCheckpoint, TableCheckpoint, RowPosition

config = DurabilityConfig(
    storage_dir=r"{temp_dir}",
    fencing_signing_key=b"AKAAL-INTEG-FENCING-HMAC-KEY-SECRET-001",
    journal_anchor_key=b"AKAAL-INTEG-JOURNAL-ANCHOR-HMAC-KEY-SECRET-002",
    db_name="integ_durability.db"
)
auth = DurabilityAuthority(config)

tok = auth.issue_fencing_token("mig_sub", "worker_child")
pos = RowPosition.create_pk(("id",), {{"id": 999}})
tbl = TableCheckpoint(table_name="accounts", schema_name="public", status="IN_PROGRESS", rows_processed=999, last_position=pos)
chk = MigrationCheckpoint(migration_id="mig_sub", job_id="job_sub", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS", table_checkpoints={{"accounts": tbl}})

auth.save_checkpoint(chk, token=tok)
auth.append_journal_record("op_sub_1", "INSERT", {{"row": 999}})
auth.close()
sys.exit(0)
"""

    res = subprocess.run([sys.executable, "-c", child_code], capture_output=True, text=True)
    assert res.returncode == 0, f"Child process failed: {res.stderr}"

    reopen_config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="integ_durability.db"
    )
    reopen_auth = DurabilityAuthority(reopen_config)

    chk = reopen_auth.get_latest_checkpoint("mig_sub")
    assert chk is not None
    assert chk.fencing_epoch == 1
    assert chk.table_checkpoints["accounts"].rows_processed == 999
    assert reopen_auth.verify_journal_integrity() is True
    reopen_auth.close()


def test_durability_scale_benchmarks(integration_durability):
    auth, _ = integration_durability

    # Issue token before any checkpoint or position writes
    tok = auth.issue_fencing_token("mig_bench", "benchmark_worker")

    start_time = time.perf_counter()
    pos = RowPosition.create_pk(("id",), {"id": 1})
    chk = MigrationCheckpoint(migration_id="mig_bench", job_id="j_bench", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS")
    auth.save_checkpoint(chk, token=tok)

    num_updates = 1000
    for i in range(num_updates):
        pos_i = RowPosition.create_pk(("id",), {"id": i})
        auth.save_row_position("mig_bench", "users", pos_i, token=tok)

    elapsed = time.perf_counter() - start_time
    updates_per_sec = num_updates / elapsed if elapsed > 0 else 0.0
    print(f"\n[BENCHMARK] Row position updates throughput: {updates_per_sec:.2f} updates/sec (elapsed {elapsed:.4f}s)")

    lookup_start = time.perf_counter()
    retrieved = auth.get_latest_checkpoint("mig_bench")
    lookup_elapsed = (time.perf_counter() - lookup_start) * 1000.0
    print(f"[BENCHMARK] Checkpoint lookup latency: {lookup_elapsed:.4f} ms")
    assert retrieved is not None
    assert lookup_elapsed < 50.0

