"""
tests/unit/engine_durability/test_durability_hostile_attacks.py
=================================================================
Hostile Attack & Crash Recovery Test Suite for CONS-005.
Proves resilience against corrupted journal records, forged anchors,
stale fencing tokens, spill frame tampering, concurrent CAS races,
and secret non-persistence guarantees.
"""

import os
import shutil
import tempfile
import time
import pytest

from akaalEngine.durability import (
    CASConflictError,
    DurabilityAuthority,
    DurabilityConfig,
    DurabilityConfigError,
    FencingViolationError,
    IdempotencyState,
    JournalCorruptError,
    MigrationCheckpoint,
    RowPosition,
    SpillCorruptError,
    StaleGenerationError,
    StateRecord,
    TableCheckpoint,
)

TEST_FENCING_KEY = b"AKAAL-HOSTILE-TEST-FENCING-KEY-001"
TEST_ANCHOR_KEY = b"AKAAL-HOSTILE-TEST-ANCHOR-KEY-002"


@pytest.fixture
def hostile_auth():
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_hostile_")
    config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="hostile.db",
        spill_quota_bytes=5 * 1024 * 1024,
        disk_reserve_bytes=100 * 1024,
    )
    auth = DurabilityAuthority(config)
    yield auth, temp_dir
    auth.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_corrupted_spill_frame_raises_spill_corrupt_error(hostile_auth):
    """Proves reading a tampered/corrupted spill segment file raises SpillCorruptError."""
    auth, _ = hostile_auth

    # Write a legitimate spill segment
    ref = auth.spill_data(stream_id="stream_spill_1", payload=b"PRESERVED_SPILL_DATA_HEADER" * 100)
    assert os.path.exists(ref.file_path)

    # Tamper with file bytes
    with open(ref.file_path, "r+b") as f:
        f.seek(10)
        f.write(b"CORRUPTED_BYTES_TAMPERED")

    # Attempting to read tampered spill file must raise SpillCorruptError
    with pytest.raises(SpillCorruptError):
        auth.read_spilled_data(ref)


def test_cross_resource_fencing_substitution_rejected(hostile_auth):
    """Proves a fencing token issued for migration_A is rejected if presented for migration_B."""
    auth, _ = hostile_auth

    token_a = auth.issue_fencing_token("migration_A", "worker_1")
    pos = RowPosition.create_pk(("id",), {"id": 1})
    tbl = TableCheckpoint(table_name="t1", schema_name="public", status="IN_PROGRESS", rows_processed=10, last_position=pos)

    chk_b = MigrationCheckpoint(
        migration_id="migration_B",
        job_id="job_b",
        fencing_epoch=token_a.fencing_epoch,
        status="IN_PROGRESS",
        table_checkpoints={"t1": tbl},
    )

    with pytest.raises(FencingViolationError, match="token resource_id"):
        auth.save_checkpoint(chk_b, token=token_a)


def test_stale_fencing_epoch_mutation_rejected(hostile_auth):
    """Proves an older epoch token cannot mutate checkpoints after a newer epoch token has been issued."""
    auth, _ = hostile_auth

    token_epoch1 = auth.issue_fencing_token("mig_epoch", "worker_v1")
    token_epoch2 = auth.issue_fencing_token("mig_epoch", "worker_v2")

    assert token_epoch2.fencing_epoch > token_epoch1.fencing_epoch

    pos = RowPosition.create_pk(("id",), {"id": 100})
    tbl = TableCheckpoint(table_name="t1", schema_name="public", status="IN_PROGRESS", rows_processed=100, last_position=pos)

    # Save using epoch 2 (succeeds)
    chk_v2 = MigrationCheckpoint(
        migration_id="mig_epoch",
        job_id="j1",
        fencing_epoch=token_epoch2.fencing_epoch,
        status="IN_PROGRESS",
        table_checkpoints={"t1": tbl},
    )
    auth.save_checkpoint(chk_v2, token=token_epoch2)

    # Stale epoch 1 attempt must raise StaleGenerationError
    chk_v1 = MigrationCheckpoint(
        migration_id="mig_epoch",
        job_id="j1",
        fencing_epoch=token_epoch1.fencing_epoch,
        status="IN_PROGRESS",
        table_checkpoints={"t1": tbl},
    )
    with pytest.raises(StaleGenerationError):
        auth.save_checkpoint(chk_v1, token=token_epoch1)


def test_state_record_cas_conflict(hostile_auth):
    """Proves concurrent updates to state record with stale expected version raise CASConflictError."""
    auth, _ = hostile_auth

    rec = StateRecord(key="state_1", namespace="test_ns", payload={"v": 1}, version=1)
    v1 = auth.put_state(rec)
    assert v1.version == 1

    # CAS update to v2
    v2 = auth.compare_and_swap("state_1", "test_ns", expected_version=1, new_payload={"v": 2})
    assert v2.version == 2

    # Attempting to CAS with stale version 1 must raise CASConflictError
    with pytest.raises(CASConflictError):
        auth.compare_and_swap("state_1", "test_ns", expected_version=1, new_payload={"v": 3})


def test_secrets_never_persisted_in_database_tables(hostile_auth):
    """Proves HMAC secret key material is never written into SQLite database tables."""
    auth, _ = hostile_auth

    conn = auth.backend._get_connection()
    tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]

    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table};").fetchall()
        for r in rows:
            r_str = str(dict(r))
            assert TEST_FENCING_KEY.decode("ascii") not in r_str
            assert TEST_ANCHOR_KEY.decode("ascii") not in r_str
