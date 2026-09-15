"""
SEC-I01 - SEC-I15: hostile/security regression matrix for the M1-M8
DAG-driven physical execution correction (`akaal.engine.facade.AkaalSuperEngine`,
`akaal.engine.plan_dispatch.PlanExecutionDispatcher`,
`akaalEngine.durability.DurabilityAuthority`).

No SEC-I-numbered test file existed anywhere in this repository before this
session (confirmed by repository-wide search) -- this is new coverage, not a
replacement or weakening of any existing suite.

Every test here exercises REAL production code paths (the real
`AkaalSuperEngine`, the real `PlanExecutionDispatcher`, the real, on-disk
SQLite-backed `DurabilityAuthority`) -- no mocking of the authority under
test. Where a real target database is needed, the local simulated SQLite
acceptance estate (`tests/fixtures/estate/`) is reused, exactly as
`tests/unit/engine/test_plan_driven_execution.py` already does.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile

import pytest

from akaal.engine.facade import (
    AkaalSuperEngine,
    ApprovalRequiredError,
    PlanFingerprintMismatchError,
)
from akaal.engine.plan_dispatch import PlanExecutionDispatcher
from akaalEngine.durability import (
    DurabilityAuthority,
    DurabilityConfig,
    Watermark,
    WatermarkType,
    WatermarkIdentityMismatchError,
    StaleGenerationError,
)
from akaalEngine.durability.models.checkpoint import MigrationCheckpoint

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE_BASELINE = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "source_baseline.sqlite")
M1_TARGET_SHELL = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "modes", "m1_bulk", "target_shell.sqlite")

pytestmark = pytest.mark.skipif(
    not os.path.exists(SOURCE_BASELINE),
    reason="simulated estate not built -- run: python -m tests.fixtures.estate.build_estate baseline",
)


def _sqlite_params(path):
    return {"system_type": "SQLITE", "database_name": path}


@pytest.fixture
def tmp_target(tmp_path):
    def _copy(src_path, name="target.sqlite"):
        dst = tmp_path / name
        shutil.copy(src_path, dst)
        return str(dst)
    return _copy


def _row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def _content_fingerprint(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()
        return hashlib.sha256(str(rows).encode()).hexdigest()
    finally:
        conn.close()


# =============================================================================
# SEC-I01: AUTHENTICATED != AUTHORIZED
# =============================================================================

def test_sec_i01_authenticated_but_not_approved_fails_closed():
    """A governance record existing at all (an 'identity is known / a record
    was created' analog to 'authenticated') is NOT sufficient to execute --
    only an EXPLICIT status=='approved' authorizes execution. A record with
    status='pending' (present, but not yet approved) must be refused exactly
    like a missing record."""
    eng = AkaalSuperEngine()
    workflow_id = "wf-sec-i01"
    spec_dict = {"execution_mode": "M1", "physical_spec": {"kind": "M1"}, "physical_validation_context": {"kind": "reconciliation"}}
    dag_dict = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}]}

    # Record EXISTS (identity/authentication analog) but is NOT approved.
    eng.state_store.set_state(f"{workflow_id}_approval", {"status": "pending", "approved_plan_fingerprint": None}, category="governance")

    with pytest.raises(ApprovalRequiredError):
        eng.execute_migration(workflow_id, spec_dict, dag_dict, source_params=_sqlite_params(SOURCE_BASELINE),
                               target_params=_sqlite_params(SOURCE_BASELINE), is_physical=True, is_synthetic_test=False)


# =============================================================================
# SEC-I02: identifiers are not ownership proof
# =============================================================================

def test_sec_i02_workflow_id_alone_grants_no_authority():
    """Possessing/knowing a valid-looking workflow_id is not proof of
    ownership or authorization to execute it -- with zero governance record
    under that id, execution must fail closed regardless of how well-formed
    the spec/dag look."""
    eng = AkaalSuperEngine()
    workflow_id = "wf-sec-i02-attacker-supplied-id"
    spec_dict = {"execution_mode": "M1", "physical_spec": {"kind": "M1"}, "physical_validation_context": {"kind": "reconciliation"}}
    dag_dict = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}]}

    assert eng.state_store.get_state(f"{workflow_id}_approval", default=None, category="governance") is None
    with pytest.raises(ApprovalRequiredError):
        eng.execute_migration(workflow_id, spec_dict, dag_dict, source_params=_sqlite_params(SOURCE_BASELINE),
                               target_params=_sqlite_params(SOURCE_BASELINE), is_physical=True, is_synthetic_test=False)


# =============================================================================
# SEC-I03: caller roles/scopes are not authoritative
# =============================================================================

def test_sec_i03_claimed_privileged_approver_cannot_bypass_fingerprint_check():
    """An approval record's `approved_by` field (a role/identity claim) is
    metadata only -- it is never consulted by the authorization decision.
    Claiming an all-powerful approver identity does not let a tampered
    (fingerprint-mismatched) plan execute."""
    eng = AkaalSuperEngine()
    workflow_id = "wf-sec-i03"
    spec_dict = {"execution_mode": "M1", "physical_spec": {"kind": "M1"}, "physical_validation_context": {"kind": "reconciliation"}}
    dag_approved = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}]}
    dag_tampered = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Parallel Stream Data Transport"}]}

    fp = eng.compute_plan_fingerprint(spec_dict, dag_approved)
    eng.state_store.set_state(f"{workflow_id}_approval",
                               {"status": "approved", "approved_plan_fingerprint": fp, "approved_by": "root-super-admin-CLAIMED"},
                               category="governance")

    with pytest.raises(PlanFingerprintMismatchError):
        eng.execute_migration(workflow_id, spec_dict, dag_tampered, source_params=_sqlite_params(SOURCE_BASELINE),
                               target_params=_sqlite_params(SOURCE_BASELINE), is_physical=True, is_synthetic_test=False)


# =============================================================================
# SEC-I04: central authorization record absent -> DENY
# =============================================================================

def test_sec_i04_missing_central_governance_record_denies():
    """No `akaal.core.state.state_store.CentralStateStore`-held governance
    record at all for this workflow_id (the canonical central-authority
    analog in this repository) must DENY, not default-allow."""
    eng = AkaalSuperEngine()
    workflow_id = "wf-sec-i04-no-record-at-all"
    assert eng.state_store.get_state(f"{workflow_id}_approval", default=None, category="governance") is None
    with pytest.raises(ApprovalRequiredError):
        eng.verify_governance_authorization(workflow_id, {"execution_mode": "M1"}, {"dag_stages": []})


# =============================================================================
# SEC-I05: stale ownership/lease/execution is fenced
# =============================================================================

def test_sec_i05_stale_fencing_token_cannot_save_checkpoint(tmp_path):
    d = str(tmp_path / "sec_i05")
    config = DurabilityConfig(storage_dir=d, fencing_signing_key=b"SEC-I05-FENCING-KEY-0001",
                               journal_anchor_key=b"SEC-I05-ANCHOR-KEY-0002", db_name="sec_i05.db",
                               spill_quota_bytes=5 * 1024 * 1024, disk_reserve_bytes=100 * 1024)
    auth = DurabilityAuthority(config)
    try:
        tok_old = auth.issue_fencing_token("mig-sec-i05", "worker-stale")  # epoch 1
        chk = MigrationCheckpoint(migration_id="mig-sec-i05", job_id="j1", fencing_epoch=tok_old.fencing_epoch, status="IN_PROGRESS")
        auth.save_checkpoint(chk, tok_old)

        auth.issue_fencing_token("mig-sec-i05", "worker-fresh")  # epoch 2, tok_old now stale

        stale_chk = MigrationCheckpoint(migration_id="mig-sec-i05", job_id="j1", fencing_epoch=tok_old.fencing_epoch, status="COMPLETED")
        with pytest.raises(StaleGenerationError):
            auth.save_checkpoint(stale_chk, tok_old)
    finally:
        auth.close()


# =============================================================================
# SEC-I06: plan identity mismatch fails closed
# =============================================================================

def test_sec_i06_plan_identity_mismatch_fails_closed_at_execution_gate():
    eng = AkaalSuperEngine()
    workflow_id = "wf-sec-i06"
    spec_dict = {"execution_mode": "M1", "physical_spec": {"kind": "M1"}, "physical_validation_context": {"kind": "reconciliation"}}
    dag_v1 = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}]}
    dag_v2_different_identity = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "SHA-256 Digital Trust Seal"}]}

    eng._record_test_governance_approval(workflow_id, spec_dict, dag_v1)
    with pytest.raises(PlanFingerprintMismatchError):
        eng.execute_migration(workflow_id, spec_dict, dag_v2_different_identity, source_params=_sqlite_params(SOURCE_BASELINE),
                               target_params=_sqlite_params(SOURCE_BASELINE), is_physical=True, is_synthetic_test=False)


# =============================================================================
# SEC-I07: unauthorized M5 repair fails closed
# =============================================================================

def test_sec_i07_m5_repair_never_authorized_by_default():
    dispatcher = PlanExecutionDispatcher(mode_str="M5", plan_fingerprint="fp-sec-i07", rt_ctx={})
    outcome = dispatcher._handle_repair_eligibility("Repair Eligibility & Candidate Evaluation", "repair_eligibility")
    assert outcome.success is True  # evaluating eligibility is not itself a failure
    assert outcome.details["repair_authorized"] is False
    assert outcome.details["repair_executed"] is False


# =============================================================================
# SEC-I08: M8 cannot mutate absent separately authorized repair
# =============================================================================

def test_sec_i08_m8_run_with_mismatch_never_mutates_target(tmp_target):
    target = tmp_target(M1_TARGET_SHELL, "sec_i08.sqlite")
    eng = AkaalSuperEngine()

    seed_spec = {"execution_mode": "M1", "physical_spec": {"kind": "M1"}, "physical_validation_context": {"kind": "reconciliation"},
                 "selected_scope": {"objects": [{"object_name": "IDENTITY_ACCESS_MGMT__roles", "target_object_name": "IDENTITY_ACCESS_MGMT__roles", "object_type": "Table"}]}}
    seed_dag = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Parallel Stream Data Transport"},
                                {"stage": 3, "name": "Reconciliation & Validation Node"}, {"stage": 4, "name": "SHA-256 Digital Trust Seal"}]}
    eng._record_test_governance_approval("wf-sec-i08-seed", seed_spec, seed_dag)
    eng.execute_migration("wf-sec-i08-seed", seed_spec, seed_dag, source_params=_sqlite_params(SOURCE_BASELINE),
                           target_params=_sqlite_params(target), is_physical=True, is_synthetic_test=False)

    conn = sqlite3.connect(target)
    conn.execute('UPDATE "IDENTITY_ACCESS_MGMT__roles" SET code = code || \'_SEC_I08_MUTATED\' WHERE id = 1')
    conn.commit()
    conn.close()
    fp_before = _content_fingerprint(target, "IDENTITY_ACCESS_MGMT__roles")

    m8_spec = {"execution_mode": "M8", "physical_spec": {"kind": "M8"}, "physical_validation_context": {"kind": "reconciliation"},
               "selected_scope": {"objects": [{"object_name": "IDENTITY_ACCESS_MGMT__roles", "target_object_name": "IDENTITY_ACCESS_MGMT__roles", "object_type": "Table"}]}}
    m8_dag = {"dag_stages": [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Passive Source & Target State Inspection"},
                              {"stage": 3, "name": "Deep Data Reconciliation & Integrity Verification"},
                              {"stage": 4, "name": "Repair Eligibility & Candidate Evaluation"}, {"stage": 5, "name": "SHA-256 Digital Trust Seal"}]}
    eng._record_test_governance_approval("wf-sec-i08", m8_spec, m8_dag)
    eng.execute_migration("wf-sec-i08", m8_spec, m8_dag, source_params=_sqlite_params(SOURCE_BASELINE),
                           target_params=_sqlite_params(target), is_physical=True, is_synthetic_test=False)

    fp_after = _content_fingerprint(target, "IDENTITY_ACCESS_MGMT__roles")
    assert fp_after == fp_before  # zero mutation despite a real, detected mismatch


# =============================================================================
# SEC-I09: M3 cannot invoke bulk (mode fence, defense-in-depth)
# =============================================================================

def _real_rt_ctx(tmp_path, table="IDENTITY_ACCESS_MGMT__tenants"):
    """A genuinely connectable rt_ctx (real sqlite source+target) so the
    LEGAL stages in a hostile DAG actually run for real, isolating the
    mode-fence assertion to the illegal stage specifically."""
    target = str(tmp_path / "sec_mode_fence_target.sqlite")
    shutil.copy(M1_TARGET_SHELL, target)
    return {
        "source_params": _sqlite_params(SOURCE_BASELINE),
        "target_params": _sqlite_params(target),
        "selected_scope": {"objects": [{"object_name": table, "target_object_name": table, "object_type": "Table"}]},
    }


def test_sec_i09_m3_dag_cannot_execute_transport_even_if_present(tmp_path):
    """Hostile construction: a DAG LABELED M3 but containing an illegal
    'Parallel Stream Data Transport' stage. The dispatcher's own mode fence
    (not merely PlanCompiler's emission rules) must refuse it."""
    dispatcher = PlanExecutionDispatcher(mode_str="M3", plan_fingerprint="fp-sec-i09", rt_ctx=_real_rt_ctx(tmp_path))
    stages = [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Parallel Stream Data Transport"}]
    result = dispatcher.run(stages)
    dispatcher.close()
    assert result.success is False
    discovery_outcome = next(o for o in result.stage_outcomes if o.stage_name == "Discovery & Catalog Fencing")
    assert discovery_outcome.success is True  # legal stage genuinely ran
    transport_outcome = next(o for o in result.stage_outcomes if o.stage_name == "Parallel Stream Data Transport")
    assert transport_outcome.success is False
    assert any("MODE_FENCE_VIOLATION" in e for e in transport_outcome.errors)
    assert result.rows_written == 0


# =============================================================================
# SEC-I10: M6 cannot invoke transport (mode fence, defense-in-depth)
# =============================================================================

def test_sec_i10_m6_dag_cannot_execute_transport_even_if_present(tmp_path):
    dispatcher = PlanExecutionDispatcher(mode_str="M6", plan_fingerprint="fp-sec-i10", rt_ctx=_real_rt_ctx(tmp_path))
    stages = [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Parallel Stream Data Transport"}]
    result = dispatcher.run(stages)
    dispatcher.close()
    assert result.success is False
    outcome = next(o for o in result.stage_outcomes if o.stage_name == "Parallel Stream Data Transport")
    assert any("MODE_FENCE_VIOLATION" in e for e in outcome.errors)
    assert result.rows_written == 0


# =============================================================================
# SEC-I11: M7 cannot invoke DDL (mode fence, defense-in-depth)
# =============================================================================

def test_sec_i11_m7_dag_cannot_execute_schema_deployment_even_if_present(tmp_path):
    dispatcher = PlanExecutionDispatcher(mode_str="M7", plan_fingerprint="fp-sec-i11", rt_ctx=_real_rt_ctx(tmp_path))
    stages = [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "Target Schema Structure Deployment"}]
    result = dispatcher.run(stages)
    dispatcher.close()
    assert result.success is False
    outcome = next(o for o in result.stage_outcomes if o.stage_name == "Target Schema Structure Deployment")
    assert any("MODE_FENCE_VIOLATION" in e for e in outcome.errors)


# =============================================================================
# SEC-I12: illegal DAG nodes cannot execute -- unrecognized mode fails closed entirely
# =============================================================================

def test_sec_i12_unrecognized_mode_refuses_every_stage():
    """An unrecognized mode cannot have its stages validated, so NOTHING in
    the DAG may execute: the first stage is refused directly by the mode
    fence (MODE_FENCE_VIOLATION); every stage after it is then blocked as a
    normal downstream consequence of that first refusal
    (UPSTREAM_STAGE_FAILED) -- fail-closed either way, never executed."""
    dispatcher = PlanExecutionDispatcher(mode_str="M999_NOT_A_REAL_MODE", plan_fingerprint="fp-sec-i12", rt_ctx={})
    stages = [{"stage": 1, "name": "Discovery & Catalog Fencing"}, {"stage": 2, "name": "SHA-256 Digital Trust Seal"}]
    result = dispatcher.run(stages)
    assert result.success is False
    assert all(not o.success for o in result.stage_outcomes)
    first_outcome = result.stage_outcomes[0]
    assert any("MODE_FENCE_VIOLATION" in e for e in first_outcome.errors)
    second_outcome = result.stage_outcomes[1]
    assert second_outcome.skipped_reason == "UPSTREAM_STAGE_FAILED"


# =============================================================================
# SEC-I13: failed prerequisites prevent dependent execution
# =============================================================================

def test_sec_i13_failed_prerequisite_blocks_all_downstream_stages(tmp_path):
    dispatcher = PlanExecutionDispatcher(mode_str="M3", plan_fingerprint="fp-sec-i13", rt_ctx=_real_rt_ctx(tmp_path))
    # "CDC Change Capture Initialization" -> cdc_init responsibility, legal
    # for M3 but NOT_YET_DISPATCHED (fails). Everything after it must be
    # skipped, never executed.
    stages = [
        {"stage": 1, "name": "Discovery & Catalog Fencing"},
        {"stage": 2, "name": "CDC Change Capture Initialization"},
        {"stage": 3, "name": "Reconciliation & Validation Node"},
        {"stage": 4, "name": "SHA-256 Digital Trust Seal"},
    ]
    result = dispatcher.run(stages)
    dispatcher.close()
    assert result.success is False
    discovery_outcome = next(o for o in result.stage_outcomes if o.stage_name == "Discovery & Catalog Fencing")
    assert discovery_outcome.success is True  # legitimately ran
    cdc_outcome = next(o for o in result.stage_outcomes if o.stage_name == "CDC Change Capture Initialization")
    assert cdc_outcome.success is False
    for downstream_name in ("Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"):
        downstream = next(o for o in result.stage_outcomes if o.stage_name == downstream_name)
        assert downstream.success is False
        assert downstream.skipped_reason == "UPSTREAM_STAGE_FAILED"


# =============================================================================
# SEC-I14: checkpoint/watermark state cannot be replayed across incompatible execution identity
# =============================================================================

def test_sec_i14_watermark_cannot_be_replayed_across_incompatible_plan_identity(tmp_path):
    d = str(tmp_path / "sec_i14")
    config = DurabilityConfig(storage_dir=d, fencing_signing_key=b"SEC-I14-FENCING-KEY-0001",
                               journal_anchor_key=b"SEC-I14-ANCHOR-KEY-0002", db_name="sec_i14.db",
                               spill_quota_bytes=5 * 1024 * 1024, disk_reserve_bytes=100 * 1024)
    auth = DurabilityAuthority(config)
    try:
        tok = auth.issue_fencing_token("mig-sec-i14", "worker1")
        auth.save_watermark(Watermark("mig-sec-i14", "orders", WatermarkType.NUMERIC, 100, "fp-ORIGINAL-PLAN", "exec-1", tok.fencing_epoch), tok)

        # A different (superseded/incompatible) compiled plan attempts to
        # "replay" / reuse this watermark identity.
        with pytest.raises(WatermarkIdentityMismatchError):
            auth.save_watermark(Watermark("mig-sec-i14", "orders", WatermarkType.NUMERIC, 500, "fp-DIFFERENT-INCOMPATIBLE-PLAN", "exec-2", tok.fencing_epoch), tok)

        assert auth.get_watermark("mig-sec-i14", "orders").plan_fingerprint == "fp-ORIGINAL-PLAN"
        assert auth.get_watermark("mig-sec-i14", "orders").value == 100
    finally:
        auth.close()


# =============================================================================
# SEC-I15: concurrent/stale execution cannot advance another execution's watermark
# =============================================================================

def test_sec_i15_stale_execution_cannot_advance_active_executions_watermark(tmp_path):
    d = str(tmp_path / "sec_i15")
    config = DurabilityConfig(storage_dir=d, fencing_signing_key=b"SEC-I15-FENCING-KEY-0001",
                               journal_anchor_key=b"SEC-I15-ANCHOR-KEY-0002", db_name="sec_i15.db",
                               spill_quota_bytes=5 * 1024 * 1024, disk_reserve_bytes=100 * 1024)
    auth = DurabilityAuthority(config)
    try:
        tok_v1 = auth.issue_fencing_token("mig-sec-i15", "worker-v1")  # epoch 1
        auth.save_watermark(Watermark("mig-sec-i15", "orders", WatermarkType.NUMERIC, 10, "fp-1", "exec-v1", tok_v1.fencing_epoch), tok_v1)

        tok_v2 = auth.issue_fencing_token("mig-sec-i15", "worker-v2")  # epoch 2, fresh execution takes over
        auth.save_watermark(Watermark("mig-sec-i15", "orders", WatermarkType.NUMERIC, 20, "fp-1", "exec-v2", tok_v2.fencing_epoch), tok_v2)

        # The stale v1 execution (epoch 1) is still alive somewhere (e.g. a
        # zombie worker) and attempts to advance the SAME watermark.
        with pytest.raises(StaleGenerationError):
            auth.save_watermark(Watermark("mig-sec-i15", "orders", WatermarkType.NUMERIC, 9999, "fp-1", "exec-v1", tok_v1.fencing_epoch), tok_v1)

        current = auth.get_watermark("mig-sec-i15", "orders")
        assert current.value == 20
        assert current.execution_id == "exec-v2"
    finally:
        auth.close()
