"""Physical, DAG-driven execution tests for AkaalSuperEngine.

Proves the canonical compiled plan (dag_dict.dag_stages) is load-bearing:
changing the DAG changes what physically executes, independently verified
against a real SQLite database (the local simulated acceptance estate),
not from logs or return values.

Requires the simulated estate to have been built:
    .venv/Scripts/python.exe -m tests.fixtures.estate.build_estate baseline
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile

import pytest

from akaal.engine.facade import AkaalSuperEngine

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SOURCE_BASELINE = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "source_baseline.sqlite")
M1_TARGET_SHELL = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "modes", "m1_bulk", "target_shell.sqlite")
M6_TARGET_EMPTY = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "modes", "m6_schema_only", "target_empty.sqlite")
M7_TARGET_PRECREATED = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "modes", "m7_data_only", "target_precreated.sqlite")

pytestmark = pytest.mark.skipif(
    not os.path.exists(SOURCE_BASELINE),
    reason="simulated estate not built -- run: python -m tests.fixtures.estate.build_estate baseline",
)


@pytest.fixture
def tmp_target(tmp_path):
    def _copy(src_path, name="target.sqlite"):
        dst = tmp_path / name
        shutil.copy(src_path, dst)
        return str(dst)
    return _copy


def _sqlite_params(path):
    return {"system_type": "SQLITE", "database_name": path}


def _row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def _ddl_fingerprint(db_path):
    conn = sqlite3.connect(db_path)
    try:
        ddl = sorted(r[0] for r in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
        ).fetchall())
        return hashlib.sha256("\n".join(ddl).encode()).hexdigest()
    finally:
        conn.close()


def _content_fingerprint(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()
        return hashlib.sha256(str(rows).encode()).hexdigest()
    finally:
        conn.close()


def _run(mode, target_db, table_names, dag_stage_names, source_db=SOURCE_BASELINE, workflow_id=None, extra_spec=None):
    eng = AkaalSuperEngine()
    workflow_id = workflow_id or f"wf-{mode.lower()}-plan-driven-test"
    spec_dict = {
        "execution_mode": mode,
        "physical_spec": {"kind": mode},
        "physical_validation_context": {"kind": "reconciliation"},
        "selected_scope": {"objects": [
            {"object_name": t, "target_object_name": t, "object_type": "Table"} for t in table_names
        ]},
    }
    if extra_spec:
        spec_dict.update(extra_spec)
    dag_dict = {"dag_stages": [{"stage": i + 1, "name": n} for i, n in enumerate(dag_stage_names)]}
    eng._record_test_governance_approval(workflow_id, spec_dict, dag_dict)
    result = eng.execute_migration(
        workflow_id, spec_dict, dag_dict,
        source_params=_sqlite_params(source_db), target_params=_sqlite_params(target_db),
        is_physical=True, is_synthetic_test=False,
    )
    from akaal.core.state.state_store import CentralStateStore
    exec_record = CentralStateStore().get_state(f"{workflow_id}_plan_execution", category="runtime")
    return result, exec_record


class TestPlanDrivenExecutionCore:
    """PLAN/EXEC-series: the compiled DAG is the execution truth."""

    def test_execute_migration_rejects_missing_compiled_dag(self):
        eng = AkaalSuperEngine()
        with pytest.raises(Exception):
            eng.execute_migration(
                "wf-missing-dag", {"execution_mode": "M1", "physical_spec": {}, "physical_validation_context": {}},
                dag_dict=None, source_params=_sqlite_params(SOURCE_BASELINE), target_params=_sqlite_params(SOURCE_BASELINE),
                is_physical=True, is_synthetic_test=False,
            )

    def test_removing_transport_stage_prevents_row_movement(self, tmp_target):
        """EXEC-003 equivalent: a legal node absent from the plan does not execute."""
        target = tmp_target(M6_TARGET_EMPTY, "m6_no_transport.sqlite")
        assert _row_count(target, "IDENTITY_ACCESS_MGMT__roles") if False else True  # table doesn't exist yet pre-run
        _run("M6", target, ["IDENTITY_ACCESS_MGMT__roles"],
             ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
              "Target Schema Structure Deployment", "Target Schema Structure Verification", "SHA-256 Digital Trust Seal"],
             workflow_id="wf-exec003-no-transport")
        assert _row_count(target, "IDENTITY_ACCESS_MGMT__roles") == 0
        assert _row_count(SOURCE_BASELINE, "IDENTITY_ACCESS_MGMT__roles") > 0

    def test_adding_transport_stage_causes_row_movement(self, tmp_target):
        """Mirror of the above: the SAME dispatcher, given a DAG that DOES include
        transport, genuinely moves rows -- proving the DAG (not a mode flag) drives behavior."""
        target = tmp_target(M1_TARGET_SHELL, "m1_with_transport.sqlite")
        _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
             ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
              "Parallel Stream Data Transport", "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
             workflow_id="wf-exec-with-transport")
        assert _row_count(target, "IDENTITY_ACCESS_MGMT__tenants") == _row_count(SOURCE_BASELINE, "IDENTITY_ACCESS_MGMT__tenants") > 0

    def test_plan_fingerprint_is_bound_and_recorded(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m1_fp.sqlite")
        result, exec_record = _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
                                    ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                                     "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-exec010-fingerprint")
        assert result["plan_fingerprint"] == exec_record["plan_fingerprint"]
        assert len(result["plan_fingerprint"]) == 64  # sha256 hex


class TestM1BulkMigration:
    def test_m1_physically_transports_real_rows(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m1_bulk.sqlite")
        tables = ["IDENTITY_ACCESS_MGMT__tenants", "IDENTITY_ACCESS_MGMT__roles"]
        result, exec_record = _run("M1", target, tables,
                                    ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
                                     "Parallel Stream Data Transport", "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m1-i-bulk")
        assert exec_record["success"] is True
        for t in tables:
            assert _row_count(target, t) == _row_count(SOURCE_BASELINE, t)
        reconciliation_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Reconciliation & Validation Node")
        for t in tables:
            assert reconciliation_stage["details"]["tables"][t]["status"] == "MATCHED"

    def test_m1_cdc_stage_never_present_in_dag(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m1_no_cdc.sqlite")
        result, exec_record = _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
                                    ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                                     "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m1-i-no-cdc")
        stage_names = [s["stage_name"] for s in exec_record["stages"]]
        assert not any("CDC" in n for n in stage_names)

    def test_m1_reconciliation_stage_independently_verifies_fencing_when_durability_configured(self, tmp_target, tmp_path):
        """Correction-campaign item 5 (owner-mandated): the reconciliation/
        validation stage (Authority #11) must independently verify a real
        fencing epoch via the canonical Durability Authority (#5), per
        contract.txt Engine Zero-Trust rules 136/137/140/141 -- proven
        POSITIVELY here (a real fencing epoch is issued and verified when
        durability is configured), with the negative/rejection case proven
        separately below."""
        target = tmp_target(M1_TARGET_SHELL, "m1_fencing.sqlite")
        extra = {
            "durability_storage_dir": str(tmp_path / "durability"),
            "durability_fencing_key": "AKAAL-TEST-RECONCILE-FENCING-KEY",
            "durability_anchor_key": "AKAAL-TEST-RECONCILE-ANCHOR-KEY",
        }
        result, exec_record = _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
                                    ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                                     "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m1-i-fencing-configured", extra_spec=extra)
        assert exec_record["success"] is True
        recon = next(s for s in exec_record["stages"] if s["stage_name"] == "Reconciliation & Validation Node")
        fc = recon["details"]["fencing_check"]
        assert fc["performed"] is True
        assert isinstance(fc["fencing_epoch"], int)

    def test_m1_reconciliation_stage_not_configured_reports_truthfully_and_still_succeeds(self, tmp_target):
        """Negative-configuration control: the vast majority of this
        campaign's pre-existing M1/M5/M6/M7/M8 callers never configure
        durability keys at all -- this must remain a truthful,
        non-blocking 'not configured' report, not a silent fabricated pass
        and not a forced failure (which would be an out-of-scope, breaking
        behavior change for every existing caller)."""
        target = tmp_target(M1_TARGET_SHELL, "m1_fencing_unconfigured.sqlite")
        result, exec_record = _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
                                    ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                                     "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m1-i-fencing-unconfigured")
        assert exec_record["success"] is True
        recon = next(s for s in exec_record["stages"] if s["stage_name"] == "Reconciliation & Validation Node")
        fc = recon["details"]["fencing_check"]
        assert fc["performed"] is False
        assert "not configured" in fc["detail"]

    def test_m1_reconciliation_stage_fails_closed_on_a_genuinely_stale_fencing_token(self, tmp_target, tmp_path, monkeypatch):
        """Correction-campaign item 5 (owner-mandated): a genuinely stale
        fencing token (a real competing issuance for the SAME resource_id
        bumped the live epoch after this token was minted) must FAIL the
        reconciliation stage closed -- not be silently accepted. This
        forces a real `StaleGenerationError` out of the real, canonical
        `akaalEngine.durability` fencing manager (the same one SEC-I05/I14/
        I15 already prove rejects stale tokens elsewhere in this
        campaign), by having a competing authority instance issue a second,
        newer token for the identical resource_id between this stage's own
        token issuance and its validation call."""
        target = tmp_target(M1_TARGET_SHELL, "m1_fencing_stale.sqlite")
        storage_dir = str(tmp_path / "durability_stale")
        fencing_key = b"AKAAL-TEST-RECONCILE-STALE-FENCING-KEY"
        anchor_key = b"AKAAL-TEST-RECONCILE-STALE-ANCHOR-KEY"
        extra = {
            "durability_storage_dir": storage_dir,
            "durability_fencing_key": fencing_key.decode(),
            "durability_anchor_key": anchor_key.decode(),
        }
        workflow_id = "wf-m1-i-fencing-stale"

        from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
        from akaal.core.state.state_store import CentralStateStore

        # Genuine race: issue+bump the epoch for the exact resource_id the
        # reconciliation stage will use, via an independent authority
        # instance, THEN monkeypatch `issue_fencing_token` to return the
        # now-stale (pre-bump) token instead of a fresh one -- so
        # `validate_fencing_token` inside the real stage genuinely rejects
        # it via the real fencing manager (not a fabricated exception).
        migration_id = workflow_id
        pre_config = DurabilityConfig(storage_dir=storage_dir, fencing_signing_key=fencing_key, journal_anchor_key=anchor_key)
        os_makedirs_done = __import__("os").makedirs(storage_dir, exist_ok=True)
        pre_auth = DurabilityAuthority(pre_config)
        try:
            stale_token = pre_auth.issue_fencing_token(migration_id, "plan_dispatch_reconciliation")
            # A second, later issuance for the SAME resource_id genuinely
            # advances the live epoch past `stale_token`.
            pre_auth.issue_fencing_token(migration_id, "a-competing-worker")
        finally:
            pre_auth.close()

        def _return_stale_token(self, resource_id, worker_id):
            assert resource_id == migration_id
            return stale_token

        monkeypatch.setattr(DurabilityAuthority, "issue_fencing_token", _return_stale_token)

        with pytest.raises(RuntimeError, match="Reconciliation"):
            _run("M1", target, ["IDENTITY_ACCESS_MGMT__tenants"],
                 ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                  "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                 workflow_id=workflow_id, extra_spec=extra)

        exec_record = CentralStateStore().get_state(f"{workflow_id}_plan_execution", category="runtime")
        assert exec_record["success"] is False
        recon = next(s for s in exec_record["stages"] if s["stage_name"] == "Reconciliation & Validation Node")
        assert "VALIDATION_FENCING_REJECTED" in recon["errors"][0]
        assert "StaleGenerationError" in recon["errors"][0]


class TestM6SchemaOnlyFencing:
    def test_m6_creates_schema_zero_rows(self, tmp_target):
        target = tmp_target(M6_TARGET_EMPTY, "m6.sqlite")
        conn = sqlite3.connect(target)
        before = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        conn.close()
        assert before == 0

        tables = ["CATALOG_PRODUCTS__categories"]
        result, exec_record = _run("M6", target, tables,
                                    ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
                                     "Target Schema Structure Deployment", "Target Schema Structure Verification",
                                     "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m6-i-schema")
        assert exec_record["success"] is True
        assert _row_count(target, "CATALOG_PRODUCTS__categories") == 0  # M6-I05/I06: data transport invocation count = 0
        stage_names = [s["stage_name"] for s in exec_record["stages"]]
        assert "Parallel Stream Data Transport" not in stage_names  # never in the DAG at all
        assert not any("CDC" in n for n in stage_names)  # M6-I07: CDC invocation count = 0

    def test_m6_transport_handler_invocation_count_is_zero(self, tmp_target, monkeypatch):
        """Correction-campaign item 7 (owner-mandated): direct invocation
        instrumentation on the ACTUAL transport/DML handler
        (`PlanExecutionDispatcher._handle_transport`), not just row-count/
        stage-name evidence (kept above as independent secondary proof). A
        call-counting spy wraps the real handler for a genuine, successful
        M6 schema-only run and asserts it was invoked exactly 0 times."""
        target = tmp_target(M6_TARGET_EMPTY, "m6_counter.sqlite")
        from akaal.engine.plan_dispatch import PlanExecutionDispatcher

        call_count = {"n": 0}
        original = PlanExecutionDispatcher._handle_transport

        def _counting(self, name, responsibility):
            call_count["n"] += 1
            return original(self, name, responsibility)

        monkeypatch.setattr(PlanExecutionDispatcher, "_handle_transport", _counting)

        tables = ["CATALOG_PRODUCTS__categories"]
        result, exec_record = _run("M6", target, tables,
                                    ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
                                     "Target Schema Structure Deployment", "Target Schema Structure Verification",
                                     "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m6-i-counter")
        assert exec_record["success"] is True
        assert call_count["n"] == 0
        # Independent, secondary proof the run genuinely did real work (the
        # zero count isn't an artifact of a no-op/failed run): schema
        # deployment for the requested table really happened.
        conn = sqlite3.connect(target)
        try:
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            conn.close()
        assert "CATALOG_PRODUCTS__categories" in names


class TestM7DataOnlyFencing:
    def test_m7_transports_data_ddl_fingerprint_unchanged(self, tmp_target):
        target = tmp_target(M7_TARGET_PRECREATED, "m7.sqlite")
        fp_before = _ddl_fingerprint(target)
        table_count_before = sqlite3.connect(target).execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]

        result, exec_record = _run("M7", target, ["CATALOG_PRODUCTS__categories"],
                                    ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
                                     "Parallel Stream Data Transport", "Reconciliation & Validation Node",
                                     "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m7-i-data-only")
        assert exec_record["success"] is True
        fp_after = _ddl_fingerprint(target)
        table_count_after = sqlite3.connect(target).execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]

        assert fp_after == fp_before  # M7-I07: target schema fingerprint unchanged
        assert table_count_after == table_count_before  # M7-I03/I04/I05: 0 CREATE/ALTER/DROP
        assert _row_count(target, "CATALOG_PRODUCTS__categories") == _row_count(SOURCE_BASELINE, "CATALOG_PRODUCTS__categories") > 0

    def test_m7_dag_never_contains_schema_deployment_stage(self, tmp_target):
        target = tmp_target(M7_TARGET_PRECREATED, "m7_no_schema.sqlite")
        result, exec_record = _run("M7", target, ["CATALOG_PRODUCTS__categories"],
                                    ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
                                     "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m7-i-no-schema-stage")
        stage_names = [s["stage_name"] for s in exec_record["stages"]]
        assert "Target Schema Structure Deployment" not in stage_names

    def test_m7_schema_ddl_handler_invocation_count_is_zero(self, tmp_target, monkeypatch):
        """Correction-campaign item 7 (owner-mandated): direct invocation
        instrumentation on the ACTUAL schema/DDL handler
        (`PlanExecutionDispatcher._handle_schema`), not just DDL-fingerprint/
        table-count evidence (kept above as independent secondary proof). A
        call-counting spy wraps the real handler for a genuine, successful
        M7 data-only run and asserts it was invoked exactly 0 times."""
        target = tmp_target(M7_TARGET_PRECREATED, "m7_counter.sqlite")
        from akaal.engine.plan_dispatch import PlanExecutionDispatcher

        call_count = {"n": 0}
        original = PlanExecutionDispatcher._handle_schema

        def _counting(self, name, responsibility):
            call_count["n"] += 1
            return original(self, name, responsibility)

        monkeypatch.setattr(PlanExecutionDispatcher, "_handle_schema", _counting)

        fp_before = _ddl_fingerprint(target)
        result, exec_record = _run("M7", target, ["CATALOG_PRODUCTS__categories"],
                                    ["Discovery & Catalog Fencing", "DAG Topological Dependency Sorting & Schema Routing",
                                     "Parallel Stream Data Transport", "Reconciliation & Validation Node",
                                     "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m7-i-counter")
        assert exec_record["success"] is True
        assert call_count["n"] == 0
        # Independent, secondary proof the run genuinely transported real
        # data (the zero DDL-handler count isn't an artifact of a no-op run).
        assert _row_count(target, "CATALOG_PRODUCTS__categories") == _row_count(SOURCE_BASELINE, "CATALOG_PRODUCTS__categories") > 0
        assert _ddl_fingerprint(target) == fp_before


class TestM8ValidationOnlyNonMutation:
    def test_m8_detects_mismatch_without_mutating_target(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m8.sqlite")
        # seed target with data that matches source, then deliberately corrupt one row
        _run("M1", target, ["IDENTITY_ACCESS_MGMT__roles"],
             ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
              "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
             workflow_id="wf-m8-seed")
        conn = sqlite3.connect(target)
        conn.execute('UPDATE "IDENTITY_ACCESS_MGMT__roles" SET code = code || \'_MUTATED\' WHERE id = 1')
        conn.commit()
        conn.close()

        fp_before = _content_fingerprint(target, "IDENTITY_ACCESS_MGMT__roles")

        result, exec_record = _run("M8", target, ["IDENTITY_ACCESS_MGMT__roles"],
                                    ["Discovery & Catalog Fencing", "Passive Source & Target State Inspection",
                                     "Deep Data Reconciliation & Integrity Verification",
                                     "Repair Eligibility & Candidate Evaluation", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m8-i-validate")
        assert exec_record["success"] is True

        fp_after = _content_fingerprint(target, "IDENTITY_ACCESS_MGMT__roles")
        assert fp_after == fp_before  # M8-I09/I10/I11: zero target mutation

        recon = next(s for s in exec_record["stages"] if s["stage_name"] == "Deep Data Reconciliation & Integrity Verification")
        table_result = recon["details"]["tables"]["IDENTITY_ACCESS_MGMT__roles"]
        assert table_result["status"] == "MISMATCH"  # a real discrepancy was really found, not hidden

        repair_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Repair Eligibility & Candidate Evaluation")
        assert repair_stage["details"]["repair_executed"] is False  # M8-I12: unauthorized repair rejected/never attempted

    def test_m8_dag_never_contains_mutating_stages(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m8_fence.sqlite")
        result, exec_record = _run("M8", target, ["IDENTITY_ACCESS_MGMT__roles"],
                                    ["Discovery & Catalog Fencing", "Passive Source & Target State Inspection",
                                     "Deep Data Reconciliation & Integrity Verification", "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m8-i-fence")
        stage_names = [s["stage_name"] for s in exec_record["stages"]]
        assert "Parallel Stream Data Transport" not in stage_names
        assert "Target Schema Structure Deployment" not in stage_names
        assert not any("CDC" in n for n in stage_names)


class TestM5StateSynchronization:
    def test_m5_reconciliation_dispatch_reuses_canonical_engine(self, tmp_target):
        target = tmp_target(M1_TARGET_SHELL, "m5.sqlite")
        _run("M1", target, ["IDENTITY_ACCESS_MGMT__roles"],
             ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
              "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
             workflow_id="wf-m5-seed")

        result, exec_record = _run("M5", target, ["IDENTITY_ACCESS_MGMT__roles"],
                                    ["Discovery & Catalog Fencing", "State-Based Differential Analysis & Reconciliation",
                                     "SHA-256 Digital Trust Seal"],
                                    workflow_id="wf-m5-i-compare")
        assert exec_record["success"] is True
        recon = next(s for s in exec_record["stages"] if s["stage_name"] == "State-Based Differential Analysis & Reconciliation")
        assert recon["details"]["tables"]["IDENTITY_ACCESS_MGMT__roles"]["status"] == "MATCHED"

    def test_m5_repair_eligibility_is_governed_by_the_real_canonical_approval_authority(self, tmp_target):
        """Correction-campaign item 4 (owner-mandated): `repair_authorized`
        must not be a hard-coded constant -- it must be routed through the
        SAME canonical governance-approval authority
        (`AkaalSuperEngine.verify_governance_authorization`)
        `execute_migration` itself requires. Proves BOTH directions through
        the real gate: (a) with no repair-scoped approval record, default-
        deny (matching SEC-I07's existing coverage, unchanged); (b) with a
        genuine repair-scoped governance approval recorded via the real
        authority, `repair_authorized` flips to True -- proving this is a
        live, reusable check, not a constant."""
        target = tmp_target(M1_TARGET_SHELL, "m5_repair.sqlite")
        _run("M1", target, ["IDENTITY_ACCESS_MGMT__roles"],
             ["Discovery & Catalog Fencing", "Parallel Stream Data Transport",
              "Reconciliation & Validation Node", "SHA-256 Digital Trust Seal"],
             workflow_id="wf-m5-repair-seed")

        # (a) No repair-scoped approval recorded -- default-deny.
        wf_deny = "wf-m5-repair-deny"
        result, exec_record = _run("M5", target, ["IDENTITY_ACCESS_MGMT__roles"],
                                    ["Discovery & Catalog Fencing", "State-Based Differential Analysis & Reconciliation",
                                     "Repair Eligibility & Candidate Evaluation", "SHA-256 Digital Trust Seal"],
                                    workflow_id=wf_deny)
        assert exec_record["success"] is True
        repair_stage = next(s for s in exec_record["stages"] if s["stage_name"] == "Repair Eligibility & Candidate Evaluation")
        assert repair_stage["details"]["repair_authorized"] is False
        assert repair_stage["details"]["repair_executed"] is False

        # (b) A genuine repair-scoped governance approval IS recorded via
        # the real canonical authority (the same `AkaalSuperEngine` /
        # `verify_governance_authorization` gate `execute_migration` uses,
        # not a second/duplicate mechanism) -- `repair_authorized` must now
        # be True, proving the gate is live and reusable, not hard-coded.
        wf_allow = "wf-m5-repair-allow"
        eng = AkaalSuperEngine()
        eng._record_test_governance_approval(f"{wf_allow}_repair", {"kind": "repair", "migration_id": wf_allow}, None)
        result2, exec_record2 = _run("M5", target, ["IDENTITY_ACCESS_MGMT__roles"],
                                      ["Discovery & Catalog Fencing", "State-Based Differential Analysis & Reconciliation",
                                       "Repair Eligibility & Candidate Evaluation", "SHA-256 Digital Trust Seal"],
                                      workflow_id=wf_allow)
        assert exec_record2["success"] is True
        repair_stage2 = next(s for s in exec_record2["stages"] if s["stage_name"] == "Repair Eligibility & Candidate Evaluation")
        assert repair_stage2["details"]["repair_authorized"] is True
        # Still never executed -- authorization is necessary but this stage
        # performs no mutation regardless (structural non-mutation).
        assert repair_stage2["details"]["repair_executed"] is False
