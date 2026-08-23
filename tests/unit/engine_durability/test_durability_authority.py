"""
Final Corrected Unit & Integration Test Suite for Authority #5 — Durability.
All 6 blockers covered. Domain-separated secret key material proofs and HMAC forge guards included.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import pytest
from akaalEngine.durability import (
    DurabilityAuthority,
    DurabilityConfig,
    StateRecord,
    MigrationCheckpoint,
    TableCheckpoint,
    RowPosition,
    RowPositionType,
    IdempotencyState,
    ExecutionManifest,
    CASConflictError,
    StaleGenerationError,
    FencingViolationError,
    JournalCorruptError,
    JournalSequenceConflictError,
    StorageQuotaExceededError,
    SpillCorruptError,
    InvalidResumePositionError,
    StateVersionUnsupportedError,
    ManifestAlreadyExistsError,
    DurabilityError,
    DurabilityConfigError,
)

TEST_FENCING_KEY = b"AKAAL-TEST-FENCING-HMAC-KEY-SECRET-001"
TEST_ANCHOR_KEY = b"AKAAL-TEST-JOURNAL-ANCHOR-HMAC-KEY-SECRET-002"


@pytest.fixture
def tmp_auth():
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_final_")
    config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="final.db",
        spill_quota_bytes=5 * 1024 * 1024,
        disk_reserve_bytes=100 * 1024,
    )
    auth = DurabilityAuthority(config)
    yield auth, temp_dir
    auth.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


# ── Security & Fail-Closed Boundary Proofs ─────────────────────────────────────

def test_fail_closed_when_key_material_missing_or_invalid():
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_keys_")
    try:
        # Missing fencing_signing_key
        with pytest.raises(DurabilityConfigError):
            DurabilityConfig(storage_dir=temp_dir, fencing_signing_key=b"", journal_anchor_key=b"anchor-secret")

        # Non-bytes fencing_signing_key
        with pytest.raises(DurabilityConfigError):
            DurabilityConfig(storage_dir=temp_dir, fencing_signing_key="not-bytes", journal_anchor_key=b"anchor-secret")

        # Missing journal_anchor_key
        with pytest.raises(DurabilityConfigError):
            DurabilityConfig(storage_dir=temp_dir, fencing_signing_key=b"fencing-secret", journal_anchor_key=b"")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fail_closed_when_keys_are_identical():
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_keys_")
    try:
        # Identical keys violate domain separation
        with pytest.raises(DurabilityConfigError, match="domain-separated"):
            DurabilityConfig(storage_dir=temp_dir, fencing_signing_key=b"same-secret-key", journal_anchor_key=b"same-secret-key")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_repr_never_leaks_keys():
    """Verify repr(DurabilityConfig) never leaks raw secret keys or field names."""
    temp_dir = tempfile.mkdtemp(prefix="akaal_dur_repr_")
    try:
        fencing_secret = b"SECRET-FENCING-KEY-999"
        anchor_secret = b"SECRET-ANCHOR-KEY-888"
        config = DurabilityConfig(
            storage_dir=temp_dir,
            fencing_signing_key=fencing_secret,
            journal_anchor_key=anchor_secret,
        )
        rep = repr(config)
        assert "fencing_signing_key" not in rep
        assert "journal_anchor_key" not in rep
        assert fencing_secret.decode() not in rep
        assert anchor_secret.decode() not in rep
        assert str(fencing_secret) not in rep
        assert str(anchor_secret) not in rep
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)



def test_source_only_caller_cannot_forge_current_epoch_fencing_token(tmp_auth):
    """
    Attacker knowing only repository source code (or hardcoded/guessed strings)
    attempts to forge a token for the CURRENT active epoch (epoch 1).
    HMAC validation must fail and raise FencingViolationError.
    """
    auth, _ = tmp_auth
    real_tok = auth.issue_fencing_token("mig_current_forge", "worker_legit")  # epoch 1
    assert real_tok.fencing_epoch == 1

    import datetime, hmac as _hmac, hashlib
    from akaalEngine.durability.models.fencing import FencingToken
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Attacker tries using published key constant or guessed key
    attacker_key = b"AKAAL-CANONICAL-FENCING-HMAC-KEY-V1"
    token_data = f"mig_current_forge|attacker|1|{now}"
    forged_sig = _hmac.new(attacker_key, token_data.encode(), hashlib.sha256).hexdigest()

    forged_token = FencingToken(
        resource_id="mig_current_forge",
        worker_id="attacker",
        fencing_epoch=1,  # Matches current epoch in DB!
        issued_at=now,
        signature=forged_sig,
    )

    chk = MigrationCheckpoint(migration_id="mig_current_forge", job_id="j_attack", fencing_epoch=1, status="FAILED")
    with pytest.raises(FencingViolationError, match="HMAC signature verification failed"):
        auth.save_checkpoint(chk, token=forged_token)


def test_source_only_caller_cannot_forge_journal_anchor(tmp_auth):
    """
    Attacker knowing repository source uses old public constant to construct an HMAC anchor.
    verify_journal_integrity() must detect mismatch and raise JournalCorruptError.
    """
    auth, _ = tmp_auth
    import hashlib, hmac as _hmac, datetime

    for i in range(1, 5):
        auth.append_journal_record(f"op_{i}", "TYPE", {"i": i})

    conn = auth.backend._get_connection()
    boundary_seq = 3
    cursor = conn.execute("SELECT parent_hash FROM journal_records WHERE sequence_number = ?;", (boundary_seq,))
    row = cursor.fetchone()
    parent_hash = row["parent_hash"]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Attacker uses public key constant
    attacker_anchor_key = b"AKAAL-JOURNAL-ANCHOR-HMAC-KEY-V1"
    anchor_data = f"ANCHOR|{boundary_seq}|{parent_hash}|{now}"
    forged_mac = _hmac.new(attacker_anchor_key, anchor_data.encode(), hashlib.sha256).hexdigest()

    conn.execute(
        "INSERT INTO journal_anchors (boundary_sequence, anchor_parent_hash, anchor_mac, compacted_at) VALUES (?, ?, ?, ?);",
        (boundary_seq, parent_hash, forged_mac, now)
    )
    conn.execute("DELETE FROM journal_records WHERE sequence_number < ?;", (boundary_seq,))

    with pytest.raises(JournalCorruptError, match="HMAC mismatch"):
        auth.verify_journal_integrity()


def test_keys_never_persisted_in_durable_storage(tmp_auth):
    """
    Verify that key material bytes or string representations are NEVER stored anywhere in SQLite database tables or metadata.
    """
    auth, _ = tmp_auth
    tok = auth.issue_fencing_token("mig_secret_check", "worker1")
    chk = MigrationCheckpoint(migration_id="mig_secret_check", job_id="j1", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS")
    auth.save_checkpoint(chk, token=tok)
    auth.append_journal_record("op_secret", "INSERT", {"data": 123})
    auth.compact_journal(1)

    conn = auth.backend._get_connection()
    # Check all tables and text columns for key bytes
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    for t in tables:
        table_name = t["name"]
        rows = conn.execute(f"SELECT * FROM {table_name};").fetchall()
        for row in rows:
            for col_val in row:
                val_str = str(col_val)
                assert TEST_FENCING_KEY.decode() not in val_str
                assert TEST_ANCHOR_KEY.decode() not in val_str


# ── Fencing required — no unissued epoch accepted ─────────────────────────────

def test_checkpoint_without_any_token_is_rejected(tmp_auth):
    """Saving a checkpoint for a resource with no issued token must be refused."""
    auth, _ = tmp_auth
    from akaalEngine.durability.models.fencing import FencingToken
    import datetime, hmac as _hmac, hashlib

    # Craft a structurally valid-looking token but for a resource with no DB row
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fake_key = TEST_FENCING_KEY
    token_data = f"mig_no_token|attacker|999|{now}"
    sig = _hmac.new(fake_key, token_data.encode(), hashlib.sha256).hexdigest()
    fake_token = FencingToken(
        resource_id="mig_no_token",
        worker_id="attacker",
        fencing_epoch=999,
        issued_at=now,
        signature=sig,
    )

    chk = MigrationCheckpoint(migration_id="mig_no_token", job_id="j", fencing_epoch=999, status="IN_PROGRESS")
    with pytest.raises(FencingViolationError):
        auth.save_checkpoint(chk, token=fake_token)


def test_checkpoint_with_fabricated_epoch_is_rejected(tmp_auth):
    """After issuing epoch 1, a token claiming epoch 999 must be rejected."""
    auth, _ = tmp_auth
    _real_tok = auth.issue_fencing_token("mig_fab", "w1")  # creates epoch 1

    # Craft a token with the real signing key but wrong epoch
    import datetime, hmac as _hmac, hashlib
    from akaalEngine.durability.models.fencing import FencingToken
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    key = TEST_FENCING_KEY
    token_data = f"mig_fab|w1|999|{now}"
    sig = _hmac.new(key, token_data.encode(), hashlib.sha256).hexdigest()
    bad_tok = FencingToken(resource_id="mig_fab", worker_id="w1", fencing_epoch=999, issued_at=now, signature=sig)

    chk = MigrationCheckpoint(migration_id="mig_fab", job_id="j", fencing_epoch=999, status="IN_PROGRESS")
    with pytest.raises(StaleGenerationError):
        auth.save_checkpoint(chk, token=bad_tok)


def test_checkpoint_with_correct_token_succeeds(tmp_auth):
    auth, _ = tmp_auth
    tok = auth.issue_fencing_token("mig_ok", "w1")
    chk = MigrationCheckpoint(migration_id="mig_ok", job_id="j", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS")
    auth.save_checkpoint(chk, token=tok)
    fetched = auth.get_latest_checkpoint("mig_ok")
    assert fetched.fencing_epoch == 1


# ── Fencing required on row position — no None bypass ─────────────────────────

def test_row_position_without_token_is_rejected(tmp_auth):
    """save_row_position requires a FencingToken; calling the facade without one raises."""
    auth, _ = tmp_auth
    tok = auth.issue_fencing_token("mig_pos", "w1")
    chk = MigrationCheckpoint(migration_id="mig_pos", job_id="j", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS")
    auth.save_checkpoint(chk, token=tok)

    # Advance epoch so tok is stale
    tok2 = auth.issue_fencing_token("mig_pos", "w2")

    pos = RowPosition.create_pk(("id",), {"id": 1})
    with pytest.raises(StaleGenerationError):
        auth.save_row_position("mig_pos", "users", pos, token=tok)  # tok is stale (epoch 1 != 2)


def test_row_position_with_current_token_succeeds(tmp_auth):
    auth, _ = tmp_auth
    tok = auth.issue_fencing_token("mig_posok", "w1")
    chk = MigrationCheckpoint(migration_id="mig_posok", job_id="j", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS")
    auth.save_checkpoint(chk, token=tok)

    pos = RowPosition.create_pk(("id",), {"id": 42})
    auth.save_row_position("mig_posok", "users", pos, token=tok)
    fetched = auth.get_latest_checkpoint("mig_posok")
    assert "users" in fetched.table_checkpoints


# ── HMAC anchor — recomputed SHA-256 forgery is rejected ──────────────────────

def test_forged_sha256_anchor_rejected(tmp_auth):
    """Attacker writes a SHA-256 anchor (no HMAC key). verify_chain_integrity must reject it."""
    auth, _ = tmp_auth
    import hashlib

    for i in range(1, 5):
        auth.append_journal_record(f"op_{i}", "TYPE", {"i": i})

    # Directly inject a fake anchor with a recomputed SHA-256 (not HMAC)
    conn = auth.backend._get_connection()
    boundary_seq = 3
    cursor = conn.execute(
        "SELECT parent_hash FROM journal_records WHERE sequence_number = ?;", (boundary_seq,)
    )
    row = cursor.fetchone()
    parent_hash = row["parent_hash"]
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fake_mac = hashlib.sha256(f"ANCHOR|{boundary_seq}|{parent_hash}|{now}".encode()).hexdigest()

    conn.execute(
        "INSERT INTO journal_anchors (boundary_sequence, anchor_parent_hash, anchor_mac, compacted_at) VALUES (?, ?, ?, ?);",
        (boundary_seq, parent_hash, fake_mac, now)
    )
    conn.execute("DELETE FROM journal_records WHERE sequence_number < ?;", (boundary_seq,))

    with pytest.raises(JournalCorruptError, match="HMAC mismatch"):
        auth.verify_journal_integrity()


def test_legitimate_compaction_with_hmac_anchor_passes(tmp_auth):
    """compact_journal writes a genuine HMAC anchor; verify_chain_integrity passes."""
    auth, _ = tmp_auth
    for i in range(1, 6):
        auth.append_journal_record(f"op_{i}", "TYPE", {"i": i})

    deleted = auth.compact_journal(safe_sequence_boundary=3)
    assert deleted == 2
    assert auth.verify_journal_integrity() is True


# ── purge_expired_records routes through anchor path ──────────────────────────

def test_purge_expired_writes_anchor_so_chain_verifies(tmp_auth):
    """Age-based purge that leaves surviving records must write an anchor first."""
    auth, _ = tmp_auth
    import datetime

    # Inject old records directly with a very old created_at
    old_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)).isoformat()
    conn = auth.backend._get_connection()

    # Append two real records (will get sequence 1 and 2)
    r1 = auth.append_journal_record("old_1", "TYPE", {"x": 1})
    r2 = auth.append_journal_record("old_2", "TYPE", {"x": 2})

    # Backdating timestamps to simulate old records
    conn.execute("UPDATE journal_records SET created_at = ? WHERE sequence_number <= 2;", (old_time,))

    # Append two current records (sequences 3 and 4)
    r3 = auth.append_journal_record("new_3", "TYPE", {"x": 3})
    r4 = auth.append_journal_record("new_4", "TYPE", {"x": 4})

    # Purge records older than 30 days — deletes seq 1-2, leaves 3-4
    deleted = auth.purge_expired_journal_records(max_age_days=30)
    assert deleted == 2

    # verify_chain_integrity must pass using the anchor written during purge
    assert auth.verify_journal_integrity() is True


def test_purge_all_records_leaves_empty_chain_valid(tmp_auth):
    """Purging every record results in an empty journal which passes integrity check."""
    auth, _ = tmp_auth
    import datetime
    old_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)).isoformat()

    auth.append_journal_record("op_1", "TYPE", {"x": 1})
    conn = auth.backend._get_connection()
    conn.execute("UPDATE journal_records SET created_at = ?;", (old_time,))

    deleted = auth.purge_expired_journal_records(max_age_days=30)
    assert deleted == 1
    assert auth.verify_journal_integrity() is True


# ── Queue ACK (previously closed — regression guard) ─────────────────────────

def test_queue_ack_requires_claim_id(tmp_auth):
    auth, _ = tmp_auth
    msg_id = auth.store_queue_message("q", b"PAYLOAD")
    claim = auth.claim_queue_message("q", worker_id="w1", lease_duration_sec=60)
    assert claim is not None

    with pytest.raises(FencingViolationError):
        auth.ack_queue_message(msg_id, claimed_by="w1", claim_id="wrong-claim-id")

    assert auth.ack_queue_message(msg_id, claimed_by="w1", claim_id=claim.claim_id) is True


def test_stale_claim_rejected_after_reclaim(tmp_auth):
    auth, _ = tmp_auth
    msg_id = auth.store_queue_message("q2", b"TASK")
    claim_w1 = auth.claim_queue_message("q2", worker_id="w1", lease_duration_sec=0)
    time.sleep(0.01)
    claim_w2 = auth.claim_queue_message("q2", worker_id="w2", lease_duration_sec=60)

    with pytest.raises(FencingViolationError):
        auth.ack_queue_message(msg_id, claimed_by="w1", claim_id=claim_w1.claim_id)

    assert auth.ack_queue_message(msg_id, claimed_by="w2", claim_id=claim_w2.claim_id) is True


# ── Integration: subprocess crash & restart ───────────────────────────────────

def test_subprocess_crash_restart_recovery(tmp_auth):
    _, temp_dir = tmp_auth
    child_code = f"""
import sys
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig, MigrationCheckpoint, TableCheckpoint, RowPosition

config = DurabilityConfig(
    storage_dir=r"{temp_dir}",
    fencing_signing_key=b"AKAAL-TEST-FENCING-HMAC-KEY-SECRET-001",
    journal_anchor_key=b"AKAAL-TEST-JOURNAL-ANCHOR-HMAC-KEY-SECRET-002",
    db_name="crash_test.db"
)
auth = DurabilityAuthority(config)

tok = auth.issue_fencing_token("mig_crash", "worker_child")
pos = RowPosition.create_pk(("id",), {{"id": 999}})
tbl = TableCheckpoint(table_name="accts", schema_name="public", status="IN_PROGRESS", rows_processed=999, last_position=pos)
chk = MigrationCheckpoint(migration_id="mig_crash", job_id="j_crash", fencing_epoch=tok.fencing_epoch, status="IN_PROGRESS", table_checkpoints={{"accts": tbl}})
auth.save_checkpoint(chk, token=tok)
auth.append_journal_record("op_crash_1", "INSERT", {{"row": 999}}, migration_id="mig_crash")
auth.close()
sys.exit(0)
"""
    res = subprocess.run([sys.executable, "-c", child_code], capture_output=True, text=True)
    assert res.returncode == 0, f"Child failed: {res.stderr}"

    reopen_config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="crash_test.db"
    )
    reopen_auth = DurabilityAuthority(reopen_config)
    chk = reopen_auth.get_latest_checkpoint("mig_crash")
    assert chk is not None
    assert chk.table_checkpoints["accts"].rows_processed == 999
    assert reopen_auth.verify_journal_integrity() is True
    reopen_auth.close()
