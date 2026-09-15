"""
M4 correction: durable watermark authority tests, physically exercised
against the real, extended `akaalEngine.durability.DurabilityAuthority`
(SQLite-backed, on-disk, real BEGIN IMMEDIATE/COMMIT transactions -- not a
mock of the thing under test).

Proves, against real code paths:
  - numeric / timestamp / compound watermark semantics
  - null watermark baseline (no watermark ever saved -> None)
  - tie timestamps accepted (not rejected as non-monotonic)
  - compound-key lexicographic ordering
  - non-monotonic/invalid positions fail safely (WatermarkRegressionError)
  - repeated batch/replay idempotency (same value re-saved is accepted)
  - plan/version/execution identity prevents incompatible checkpoint reuse
    (WatermarkIdentityMismatchError)
  - concurrent/stale execution cannot advance another execution's watermark
    (StaleGenerationError, via fencing epoch)
  - restart from durable watermark (close + reopen the SAME on-disk store,
    confirm the persisted value survives process-level restart)
  - a rejected/failed write leaves the previously-durable watermark
    completely unchanged (atomic all-or-nothing persistence)

Does NOT and must NOT claim cross-database atomicity between the migration
target and this durability store -- that guarantee does not exist and is
out of scope. What IS proven here: within this store's own transaction,
watermark persistence is atomic, monotonic-enforcing, and identity-fenced.
"""

import shutil
import tempfile

import pytest

from akaalEngine.durability import (
    DurabilityAuthority,
    DurabilityConfig,
    Watermark,
    WatermarkType,
    WatermarkRegressionError,
    WatermarkIdentityMismatchError,
    StaleGenerationError,
    InvalidResumePositionError,
)

TEST_FENCING_KEY = b"AKAAL-TEST-M4-FENCING-HMAC-KEY-SECRET-001"
TEST_ANCHOR_KEY = b"AKAAL-TEST-M4-JOURNAL-ANCHOR-HMAC-KEY-SECRET-002"


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="akaal_dur_m4_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _open(tmp_dir):
    config = DurabilityConfig(
        storage_dir=tmp_dir,
        fencing_signing_key=TEST_FENCING_KEY,
        journal_anchor_key=TEST_ANCHOR_KEY,
        db_name="m4.db",
        spill_quota_bytes=5 * 1024 * 1024,
        disk_reserve_bytes=100 * 1024,
    )
    return DurabilityAuthority(config)


# -- null watermark baseline -------------------------------------------------

def test_no_watermark_ever_saved_returns_none(tmp_dir):
    auth = _open(tmp_dir)
    try:
        assert auth.get_watermark("mig-m4-null", "t1") is None
    finally:
        auth.close()


# -- numeric watermark --------------------------------------------------------

def test_numeric_watermark_save_and_advance(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-num", "worker1")
        wm1 = Watermark("mig-m4-num", "orders", WatermarkType.NUMERIC, 100, "fp-1", "exec-1", tok.fencing_epoch)
        auth.save_watermark(wm1, tok)
        got = auth.get_watermark("mig-m4-num", "orders")
        assert got.value == 100

        wm2 = Watermark("mig-m4-num", "orders", WatermarkType.NUMERIC, 250, "fp-1", "exec-1", tok.fencing_epoch)
        auth.save_watermark(wm2, tok)
        assert auth.get_watermark("mig-m4-num", "orders").value == 250
    finally:
        auth.close()


def test_numeric_watermark_regression_rejected(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-numreg", "worker1")
        auth.save_watermark(Watermark("mig-m4-numreg", "orders", WatermarkType.NUMERIC, 500, "fp-1", "exec-1", tok.fencing_epoch), tok)
        with pytest.raises(WatermarkRegressionError):
            auth.save_watermark(Watermark("mig-m4-numreg", "orders", WatermarkType.NUMERIC, 100, "fp-1", "exec-1", tok.fencing_epoch), tok)
        # unchanged after the rejected write
        assert auth.get_watermark("mig-m4-numreg", "orders").value == 500
    finally:
        auth.close()


def test_numeric_watermark_null_value_fails_safe(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-numnull", "worker1")
        with pytest.raises(InvalidResumePositionError):
            auth.save_watermark(Watermark("mig-m4-numnull", "orders", WatermarkType.NUMERIC, None, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-numnull", "orders") is None
    finally:
        auth.close()


# -- timestamp watermark, including ties --------------------------------------

def test_timestamp_watermark_advance_and_tie_accepted(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-ts", "worker1")
        t1 = "2026-01-01T00:00:00+00:00"
        t2 = "2026-01-02T00:00:00+00:00"
        auth.save_watermark(Watermark("mig-m4-ts", "events", WatermarkType.TIMESTAMP, t1, "fp-1", "exec-1", tok.fencing_epoch), tok)
        auth.save_watermark(Watermark("mig-m4-ts", "events", WatermarkType.TIMESTAMP, t2, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-ts", "events").value == t2

        # exact tie (repeated batch/replay of the same boundary) must succeed, not raise
        auth.save_watermark(Watermark("mig-m4-ts", "events", WatermarkType.TIMESTAMP, t2, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-ts", "events").value == t2
    finally:
        auth.close()


def test_timestamp_watermark_regression_rejected(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-tsreg", "worker1")
        t_later = "2026-06-01T00:00:00+00:00"
        t_earlier = "2026-01-01T00:00:00+00:00"
        auth.save_watermark(Watermark("mig-m4-tsreg", "events", WatermarkType.TIMESTAMP, t_later, "fp-1", "exec-1", tok.fencing_epoch), tok)
        with pytest.raises(WatermarkRegressionError):
            auth.save_watermark(Watermark("mig-m4-tsreg", "events", WatermarkType.TIMESTAMP, t_earlier, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-tsreg", "events").value == t_later
    finally:
        auth.close()


# -- compound watermark (lexicographic tuple ordering) ------------------------

def test_compound_watermark_ordering(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-cmp", "worker1")
        # [timestamp, sequence_no] compound key: equal leading component must
        # correctly fall through to compare the tie-breaker sequence number.
        v1 = ["2026-01-01T00:00:00+00:00", 5]
        v2 = ["2026-01-01T00:00:00+00:00", 9]  # same timestamp, higher seq -> valid advance
        auth.save_watermark(Watermark("mig-m4-cmp", "ledger", WatermarkType.COMPOUND, v1, "fp-1", "exec-1", tok.fencing_epoch), tok)
        auth.save_watermark(Watermark("mig-m4-cmp", "ledger", WatermarkType.COMPOUND, v2, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-cmp", "ledger").value == v2

        v_regress = ["2026-01-01T00:00:00+00:00", 3]  # same timestamp, LOWER seq -> regression
        with pytest.raises(WatermarkRegressionError):
            auth.save_watermark(Watermark("mig-m4-cmp", "ledger", WatermarkType.COMPOUND, v_regress, "fp-1", "exec-1", tok.fencing_epoch), tok)
        assert auth.get_watermark("mig-m4-cmp", "ledger").value == v2
    finally:
        auth.close()


# -- plan/version/execution identity prevents incompatible reuse -------------

def test_incompatible_plan_fingerprint_rejected(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-plan", "worker1")
        auth.save_watermark(Watermark("mig-m4-plan", "orders", WatermarkType.NUMERIC, 10, "fp-AAA", "exec-1", tok.fencing_epoch), tok)
        with pytest.raises(WatermarkIdentityMismatchError):
            auth.save_watermark(Watermark("mig-m4-plan", "orders", WatermarkType.NUMERIC, 20, "fp-BBB-DIFFERENT-PLAN", "exec-2", tok.fencing_epoch), tok)
        # unchanged -- the incompatible plan never got to advance it
        assert auth.get_watermark("mig-m4-plan", "orders").value == 10
    finally:
        auth.close()


# -- concurrent/stale execution fencing ---------------------------------------

def test_stale_execution_cannot_advance_watermark(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok_epoch1 = auth.issue_fencing_token("mig-m4-stale", "worker1")  # epoch 1
        auth.save_watermark(Watermark("mig-m4-stale", "orders", WatermarkType.NUMERIC, 10, "fp-1", "exec-1", tok_epoch1.fencing_epoch), tok_epoch1)

        # A fresher execution takes over (new fencing epoch)
        tok_epoch2 = auth.issue_fencing_token("mig-m4-stale", "worker2")  # epoch 2
        auth.save_watermark(Watermark("mig-m4-stale", "orders", WatermarkType.NUMERIC, 20, "fp-1", "exec-2", tok_epoch2.fencing_epoch), tok_epoch2)

        # The now-stale (epoch 1) execution attempts to advance the SAME watermark -> refused
        with pytest.raises(StaleGenerationError):
            auth.save_watermark(Watermark("mig-m4-stale", "orders", WatermarkType.NUMERIC, 999, "fp-1", "exec-1", tok_epoch1.fencing_epoch), tok_epoch1)

        assert auth.get_watermark("mig-m4-stale", "orders").value == 20
    finally:
        auth.close()


# -- idempotent replay ---------------------------------------------------------

def test_repeated_identical_batch_replay_is_idempotent(tmp_dir):
    auth = _open(tmp_dir)
    try:
        tok = auth.issue_fencing_token("mig-m4-replay", "worker1")
        wm = Watermark("mig-m4-replay", "orders", WatermarkType.NUMERIC, 42, "fp-1", "exec-1", tok.fencing_epoch)
        auth.save_watermark(wm, tok)
        # Re-applying the exact same batch's resulting watermark must not raise
        # and must not corrupt the stored value.
        auth.save_watermark(wm, tok)
        auth.save_watermark(wm, tok)
        assert auth.get_watermark("mig-m4-replay", "orders").value == 42
    finally:
        auth.close()


# -- restart from durable watermark -------------------------------------------

def test_restart_from_durable_watermark_survives_process_restart(tmp_dir):
    auth1 = _open(tmp_dir)
    tok = auth1.issue_fencing_token("mig-m4-restart", "worker1")
    auth1.save_watermark(Watermark("mig-m4-restart", "orders", WatermarkType.NUMERIC, 777, "fp-1", "exec-1", tok.fencing_epoch), tok)
    auth1.close()

    # Simulate a fresh process: brand-new DurabilityAuthority instance over
    # the SAME on-disk storage_dir (no in-memory state reused).
    auth2 = _open(tmp_dir)
    try:
        restored = auth2.get_watermark("mig-m4-restart", "orders")
        assert restored is not None
        assert restored.value == 777
        assert restored.plan_fingerprint == "fp-1"
    finally:
        auth2.close()


# -- failed write leaves durable watermark unchanged (atomicity) -------------

def test_rejected_write_leaves_prior_watermark_unchanged(tmp_dir):
    """A write that fails mid-validation (here: stale fencing epoch, but the
    same atomic BEGIN IMMEDIATE/COMMIT/ROLLBACK path is exercised for every
    rejection reason) must leave the previously-persisted watermark exactly
    as it was -- no partial/corrupted state, proven by re-reading it fresh
    after the failure."""
    auth = _open(tmp_dir)
    try:
        tok1 = auth.issue_fencing_token("mig-m4-atomic", "worker1")
        auth.save_watermark(Watermark("mig-m4-atomic", "orders", WatermarkType.NUMERIC, 55, "fp-1", "exec-1", tok1.fencing_epoch), tok1)

        tok2 = auth.issue_fencing_token("mig-m4-atomic", "worker2")  # advances epoch, tok1 now stale
        with pytest.raises(StaleGenerationError):
            auth.save_watermark(Watermark("mig-m4-atomic", "orders", WatermarkType.NUMERIC, 9999, "fp-1", "exec-1", tok1.fencing_epoch), tok1)

        got = auth.get_watermark("mig-m4-atomic", "orders")
        assert got.value == 55
        assert got.fencing_epoch == tok1.fencing_epoch
    finally:
        auth.close()


# -- target-commit-before-watermark-advancement ordering discipline ----------

def test_watermark_authority_itself_has_no_target_visibility_by_design(tmp_dir):
    """Documents and enforces, at the API-surface level, why this authority
    cannot and does not claim cross-database atomicity: `save_watermark`
    takes no target-connection/commit-confirmation argument at all -- the
    invariant ("never advance the durable watermark until target work has
    safely committed") is necessarily enforced by CALL ORDER in the caller
    (the M4 incremental-poll dispatch step), not inside this store. This
    test asserts that contract's shape rather than a fabricated cross-store
    transaction that does not exist."""
    import inspect
    from akaalEngine.durability.checkpoint.registry import MigrationCheckpointRegistry
    sig = inspect.signature(MigrationCheckpointRegistry.save_watermark)
    params = set(sig.parameters.keys())
    assert "target_connection" not in params and "target_conn" not in params
