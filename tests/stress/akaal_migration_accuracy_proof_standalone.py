"""
AKAAL FINAL THREE-METRIC ACCEPTANCE TEST -- RESULT 2 evidence script.

NEW, ADDITIVE, TEST-ONLY script (invoke directly with
`.venv/Scripts/python.exe tests/stress/akaal_migration_accuracy_proof_standalone.py`).

Purpose: run a real, full-estate M1 bulk migration through the canonical
production path (`akaal.engine.facade.AkaalSuperEngine.execute_migration` ->
`akaal.engine.plan_dispatch.PlanExecutionDispatcher`) against the real
SQLite estate (tests/fixtures/estate/data/source_baseline.sqlite, all 206
tables / 1,000,000 declared rows), then INDEPENDENTLY verify the result via:
  (a) direct sqlite3 row-count queries against both source and target files
      (not trusting AKAAL's own self-reported counters), and
  (b) `akaal.validation.domain.reconciliation.CanonicalReconciliationEngine
      .reconcile_tables` called directly by this grader script on the real
      row data read back from both databases.

Zero production code is modified. This script only:
  - calls existing public APIs (`AkaalSuperEngine`, `CanonicalReconciliationEngine`,
    `CentralStateStore`, the existing test-fixture helper
    `tests/fixtures/estate/modes/_common.py::build_empty_schema_shell`, which
    this script imports but does not edit);
  - monkeypatches `PlanExecutionDispatcher._handle_transport` at runtime,
    IN THIS PROCESS ONLY, with a thin timing wrapper around the real,
    unmodified method (the same call-counting-wrapper technique already
    used by the existing test
    tests/unit/engine/test_plan_driven_execution.py::
    test_m6_transport_handler_invocation_count_is_zero) purely to capture
    the real transport-stage-only elapsed time for the
    RAW_MIGRATION_THROUGHPUT_ROWS_SEC metric, without altering behavior.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
ESTATE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "estate")
if ESTATE_DIR not in sys.path:
    sys.path.insert(0, ESTATE_DIR)

from akaal.engine.facade import AkaalSuperEngine  # noqa: E402
from akaal.engine.plan_dispatch import PlanExecutionDispatcher  # noqa: E402
from akaal.core.state.state_store import CentralStateStore  # noqa: E402
from akaal.validation.domain.reconciliation import CanonicalReconciliationEngine  # noqa: E402

from modes._common import build_empty_schema_shell  # noqa: E402
from config.domains import ALL_TABLES  # noqa: E402

SOURCE_BASELINE = os.path.join(ESTATE_DIR, "data", "source_baseline.sqlite")
EVIDENCE_DIR = os.path.join(ESTATE_DIR, "data", "modes", "_accuracy_proof_evidence")


def _full_name(t):
    return f"{t.schema}__{t.name}"


def _sqlite_params(path):
    return {"system_type": "SQLITE", "database_name": path}


def _row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def _fetch_all(db_path, table, columns):
    conn = sqlite3.connect(db_path)
    try:
        col_list = ",".join(f'"{c}"' for c in columns)
        cur = conn.execute(f'SELECT {col_list} FROM "{table}"')
        return [tuple(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _columns_of(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return [c[1] for c in conn.execute(f'PRAGMA table_info("{table}")')]
    finally:
        conn.close()


def main():
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    run_id = f"accuracy-proof-{int(time.time())}"
    target_path = os.path.join(EVIDENCE_DIR, f"target_{run_id}.sqlite")

    table_limit = os.environ.get("ACCURACY_PROOF_TABLE_LIMIT")
    scope_tables = ALL_TABLES if not table_limit else ALL_TABLES[: int(table_limit)]

    all_tables = [_full_name(t) for t in scope_tables]
    no_pk_tables = [_full_name(t) for t in scope_tables if not t.primary_key]
    pk_tables = [t for t in scope_tables if t.primary_key]

    evidence = {
        "run_id": run_id,
        "table_count": len(all_tables),
        "no_pk_table_count": len(no_pk_tables),
        "no_pk_tables": no_pk_tables,
        "source_total_rows": None,
        "target_total_rows_before": None,
        "target_total_rows_after": None,
        "exec_success": None,
        "elapsed_total_seconds": None,
        "elapsed_transport_only_seconds": None,
        "reconciliation": {},
        "no_pk_row_count_check": {},
        "error": None,
        "traceback": None,
    }

    # 1) Build a fresh, full-estate, zero-row target schema (existing
    #    test-fixture helper -- not production migration).
    ddl_fp = build_empty_schema_shell(target_path, tables=ALL_TABLES)
    evidence["target_ddl_fingerprint"] = ddl_fp

    src_total = sum(_row_count(SOURCE_BASELINE, t) for t in all_tables)
    tgt_total_before = sum(_row_count(target_path, t) for t in all_tables)
    evidence["source_total_rows"] = src_total
    evidence["target_total_rows_before"] = tgt_total_before

    workflow_id = "wf-final-three-metric-accuracy-full-estate"
    spec_dict = {
        "execution_mode": "M1",
        "physical_spec": {"kind": "M1"},
        "physical_validation_context": {"kind": "reconciliation"},
        "selected_scope": {"objects": [
            {"object_name": t, "target_object_name": t, "object_type": "Table"} for t in all_tables
        ]},
    }
    dag_dict = {"dag_stages": [
        {"stage": 1, "name": "Discovery & Catalog Fencing"},
        {"stage": 2, "name": "DAG Topological Dependency Sorting & Schema Routing"},
        {"stage": 3, "name": "Parallel Stream Data Transport"},
        {"stage": 4, "name": "Reconciliation & Validation Node"},
        {"stage": 5, "name": "SHA-256 Digital Trust Seal"},
    ]}

    eng = AkaalSuperEngine()
    eng._record_test_governance_approval(workflow_id, spec_dict, dag_dict)

    # Timing instrumentation for transport-stage-only elapsed time (RAW
    # throughput), via a thin wrapper around the real, unmodified handler --
    # same technique the existing test suite already uses for call counting.
    transport_timing = {"elapsed": None}
    original_handle_transport = PlanExecutionDispatcher._handle_transport

    def _timed_handle_transport(self, name, responsibility):
        t_start = time.perf_counter()
        outcome = original_handle_transport(self, name, responsibility)
        transport_timing["elapsed"] = time.perf_counter() - t_start
        return outcome

    PlanExecutionDispatcher._handle_transport = _timed_handle_transport

    t0 = time.perf_counter()
    try:
        result = eng.execute_migration(
            workflow_id, spec_dict, dag_dict,
            source_params=_sqlite_params(SOURCE_BASELINE),
            target_params=_sqlite_params(target_path),
            is_physical=True, is_synthetic_test=False,
        )
        t1 = time.perf_counter()
        evidence["elapsed_total_seconds"] = t1 - t0
        evidence["result_success"] = result.get("success") if isinstance(result, dict) else None
    except Exception as exc:
        t1 = time.perf_counter()
        evidence["elapsed_total_seconds"] = t1 - t0
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        evidence["traceback"] = traceback.format_exc()
    finally:
        PlanExecutionDispatcher._handle_transport = original_handle_transport
        evidence["elapsed_transport_only_seconds"] = transport_timing["elapsed"]

    exec_record = CentralStateStore().get_state(f"{workflow_id}_plan_execution", category="runtime")
    evidence["exec_success"] = exec_record.get("success") if isinstance(exec_record, dict) else None
    if isinstance(exec_record, dict):
        evidence["exec_stage_names"] = [s.get("stage_name") for s in exec_record.get("stages", [])]

    tgt_total_after = sum(_row_count(target_path, t) for t in all_tables)
    evidence["target_total_rows_after"] = tgt_total_after

    # Independent reconciliation, per PK-bearing table, via the real
    # CanonicalReconciliationEngine -- grader-side, not AKAAL's own
    # self-report.
    recon_engine = CanonicalReconciliationEngine()
    agg = {"matched": 0, "source_only": 0, "target_only": 0, "value_mismatch": 0,
           "indeterminate": 0, "error": 0, "source_rows_total": 0}
    per_table = {}
    for t in pk_tables:
        full = _full_name(t)
        cols = _columns_of(SOURCE_BASELINE, full)
        src_rows = _fetch_all(SOURCE_BASELINE, full, cols)
        tgt_rows = _fetch_all(target_path, full, cols)
        pk_cols = list(t.primary_key)
        summary, _records = recon_engine.reconcile_tables(
            table_name=full, source_rows=src_rows, target_rows=tgt_rows,
            columns=cols, pk_columns=pk_cols,
            source_dialect="sqlite", target_dialect="sqlite",
        )
        per_table[full] = {
            "status": summary.status,
            "source_rows": summary.source_rows,
            "target_rows": summary.target_rows,
            "matched_count": summary.matched_count,
            "source_only_count": summary.source_only_count,
            "target_only_count": summary.target_only_count,
            "value_mismatch_count": summary.value_mismatch_count,
            "indeterminate_count": getattr(summary, "indeterminate_count", 0),
            "error_count": getattr(summary, "error_count", 0),
        }
        agg["matched"] += summary.matched_count
        agg["source_only"] += summary.source_only_count
        agg["target_only"] += summary.target_only_count
        agg["value_mismatch"] += summary.value_mismatch_count
        agg["indeterminate"] += getattr(summary, "indeterminate_count", 0)
        agg["error"] += getattr(summary, "error_count", 0)
        agg["source_rows_total"] += summary.source_rows

    evidence["reconciliation"] = {"aggregate": agg, "per_table": per_table}

    # No-PK tables: reconciliation cannot assign row-identity MATCHED status
    # by design (no PK to key on) -- independently cross-check via direct
    # row-count-only comparison instead, reported separately (not folded
    # into the PK-scope accuracy percentage).
    no_pk_check = {}
    for full in no_pk_tables:
        s = _row_count(SOURCE_BASELINE, full)
        tg = _row_count(target_path, full)
        no_pk_check[full] = {"source_rows": s, "target_rows": tg, "row_count_equal": s == tg}
    evidence["no_pk_row_count_check"] = no_pk_check

    accuracy_pk_scope = None
    if agg["source_rows_total"] > 0:
        correct = agg["source_rows_total"] - agg["source_only"] - agg["target_only"] - agg["value_mismatch"]
        accuracy_pk_scope = (correct / agg["source_rows_total"]) * 100
    evidence["accuracy_pk_scope_percent"] = accuracy_pk_scope

    rows_per_sec_raw = None
    if transport_timing["elapsed"]:
        rows_per_sec_raw = src_total / transport_timing["elapsed"]
    rows_per_sec_e2e = None
    if evidence["elapsed_total_seconds"]:
        rows_per_sec_e2e = agg["matched"] / evidence["elapsed_total_seconds"]
    evidence["raw_throughput_rows_per_sec"] = rows_per_sec_raw
    evidence["end_to_end_validated_throughput_rows_per_sec"] = rows_per_sec_e2e

    evidence_path = os.path.join(EVIDENCE_DIR, f"evidence_{run_id}.json")
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2, default=str)

    print(json.dumps({k: v for k, v in evidence.items() if k != "reconciliation"}, indent=2, default=str))
    print("AGGREGATE_RECONCILIATION:", json.dumps(agg, indent=2))
    print(f"\nEVIDENCE_FILE={evidence_path}")


if __name__ == "__main__":
    main()
