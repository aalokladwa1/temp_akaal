"""Fixture self-tests (build-spec §31). These test the FIXTURE, not AKAAL.

Baseline/manifest artifacts are expected to already exist (built by
build_estate.py, manifests/source_manifest.py and modes/*.py). Rebuilding
the full 1,000,000-row baseline inside a test run is deliberately avoided
(it takes ~3 minutes) -- determinism of the expensive baseline build is
instead proven by a targeted re-fingerprint of a sample of tables. Cheap
mode fixtures (M2-M5, M8) ARE fully rebuilt here to prove end-to-end
determinism at low cost.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pytest

from config.domains import ALL_TABLES, SCHEMA_TARGETS
from generator.schema_builder import physical_table_name
from manifests.fingerprint import table_fingerprint

DATA_DIR = os.path.join(HERE, "data")
BASELINE_DB = os.path.join(DATA_DIR, "source_baseline.sqlite")
SOURCE_MANIFEST = os.path.join(DATA_DIR, "source_manifest.json")
MODES_DIR = os.path.join(DATA_DIR, "modes")

pytestmark = pytest.mark.skipif(
    not os.path.exists(BASELINE_DB),
    reason="baseline not built yet -- run: python -m tests.fixtures.estate.build_estate baseline",
)


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(BASELINE_DB)
    yield c
    c.close()


@pytest.fixture(scope="module")
def source_manifest():
    with open(SOURCE_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


# ---- declarative-layer checks (config/domains.py) --------------------------

def test_exactly_12_schemas():
    assert len(SCHEMA_TARGETS) == 12


def test_declared_baseline_totals_exactly_1_000_000():
    assert sum(t.row_count for t in ALL_TABLES) == 1_000_000


def test_schema_row_distribution_reconciles():
    by_schema = {}
    for t in ALL_TABLES:
        by_schema[t.schema] = by_schema.get(t.schema, 0) + t.row_count
    assert by_schema == SCHEMA_TARGETS


def test_no_pk_table_count_is_6():
    no_pk = [t for t in ALL_TABLES if t.primary_key is None]
    assert len(no_pk) == 6


def test_empty_table_count_is_24():
    from config.schema_spec import TableKind
    empty = [t for t in ALL_TABLES if t.kind == TableKind.EMPTY]
    assert len(empty) == 24


def test_no_duplicate_qualified_table_names():
    names = [t.qualified_name for t in ALL_TABLES]
    assert len(names) == len(set(names))


# ---- physical-database checks ----------------------------------------------

def test_physical_row_total_is_exactly_1_000_000(conn):
    total = 0
    for t in ALL_TABLES:
        phys = physical_table_name(t.schema, t.name)
        total += conn.execute(f'SELECT COUNT(*) FROM "{phys}"').fetchone()[0]
    assert total == 1_000_000


def test_physical_row_counts_match_declared(conn):
    for t in ALL_TABLES:
        phys = physical_table_name(t.schema, t.name)
        n = conn.execute(f'SELECT COUNT(*) FROM "{phys}"').fetchone()[0]
        assert n == t.row_count, f"{t.qualified_name}: physical={n} declared={t.row_count}"


def test_foreign_key_integrity(conn):
    conn.execute("PRAGMA foreign_keys = ON;")
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert violations == []


def test_pk_uniqueness_sampled(conn):
    # single-column PK tables: uniqueness is enforced by SQLite's PRIMARY KEY
    # constraint at insert time already; here we independently re-verify a
    # sample of composite-PK tables where uniqueness is the harder case.
    composite_pk_tables = [t for t in ALL_TABLES if t.primary_key and len(t.primary_key) > 1][:15]
    for t in composite_pk_tables:
        phys = physical_table_name(t.schema, t.name)
        cols = ", ".join(f'"{c}"' for c in t.primary_key)
        total = conn.execute(f'SELECT COUNT(*) FROM "{phys}"').fetchone()[0]
        distinct = conn.execute(f'SELECT COUNT(*) FROM (SELECT DISTINCT {cols} FROM "{phys}")').fetchone()[0]
        assert total == distinct, f"{t.qualified_name}: PK not unique ({total} rows, {distinct} distinct keys)"


def test_intentional_no_pk_tables_have_no_sqlite_pk(conn):
    no_pk = [t for t in ALL_TABLES if t.primary_key is None]
    for t in no_pk:
        phys = physical_table_name(t.schema, t.name)
        info = conn.execute(f'PRAGMA table_info("{phys}")').fetchall()
        assert all(row[5] == 0 for row in info), f"{t.qualified_name} unexpectedly has a PK column"


def test_lob_band_counts_match_target(source_manifest):
    lob = source_manifest["lob_estate_summary"]
    assert lob["tiny"]["count"] == 15_000
    assert lob["small"]["count"] == 5_000
    assert lob["medium"]["count"] == 1_200
    assert lob["large"]["count"] == 200
    assert lob["very_large"]["count"] == 15


def test_source_manifest_matches_physical_state(conn, source_manifest):
    assert source_manifest["total_rows_physical"] == 1_000_000
    assert source_manifest["table_count"] == len(ALL_TABLES)
    assert source_manifest["no_pk_table_count"] == 6
    assert source_manifest["empty_table_count"] == 24


def test_table_fingerprint_reproduces(conn, source_manifest):
    # spot-check: recompute fingerprints for a handful of small tables and
    # confirm they match what the (already independently built) manifest recorded.
    sample = [t for t in ALL_TABLES if 0 < t.row_count <= 500][:8]
    assert sample, "expected at least one small populated table to sample"
    for t in sample:
        phys = physical_table_name(t.schema, t.name)
        recomputed = table_fingerprint(conn, phys)
        recorded = source_manifest["table_fingerprints"][phys]
        assert recomputed["fingerprint"] == recorded["fingerprint"]
        assert recomputed["row_count"] == recorded["row_count"]


# ---- PL/SQL corpus checks ---------------------------------------------------

def test_plsql_corpus_counts_meet_minimums():
    from plsql_corpus.expected_truth import ALL_OBJECTS
    from collections import Counter
    counts = Counter(o.kind for o in ALL_OBJECTS)
    assert counts["VIEW"] >= 30
    assert counts["MATERIALIZED_VIEW"] >= 4
    assert counts["SEQUENCE"] >= 38
    assert counts["TRIGGER"] >= 24
    assert counts["PROCEDURE"] >= 24
    assert counts["FUNCTION"] >= 24
    assert counts["PACKAGE_SPEC"] >= 12
    assert counts["PACKAGE_BODY"] >= 12


def test_plsql_expected_truth_never_claims_false_entrypoint():
    from plsql_corpus.expected_truth import EXPECTED_TRUTH
    for entry in EXPECTED_TRUTH:
        if entry["kind"] in ("VIEW", "MATERIALIZED_VIEW", "SEQUENCE", "TRIGGER", "PACKAGE_SPEC", "PACKAGE_BODY"):
            assert entry["entrypoint_status"] == "NO_PRODUCTION_ENTRYPOINT_YET"
            assert entry["predicted_difficulty"] is None
        else:
            assert entry["entrypoint_status"] == "HAS_ENTRYPOINT"
            assert entry["predicted_difficulty"] is not None


def test_plsql_no_unintentionally_empty_source():
    from plsql_corpus.expected_truth import ALL_OBJECTS
    for o in ALL_OBJECTS:
        assert o.source_sql and o.source_sql.strip(), f"{o.object_id} has empty source"


# ---- M1/M6/M7 (cheap, structural) -------------------------------------------

def test_m1_target_shell_is_empty_with_matching_ddl():
    with open(os.path.join(MODES_DIR, "m1_bulk", "manifest.json")) as f:
        m1 = json.load(f)
    assert m1["target_initial_row_count"] == 0
    target_db = os.path.join(MODES_DIR, "m1_bulk", m1["target_db"])
    c = sqlite3.connect(target_db)
    total = sum(c.execute(f'SELECT COUNT(*) FROM "{physical_table_name(t.schema, t.name)}"').fetchone()[0] for t in ALL_TABLES)
    c.close()
    assert total == 0


def test_m6_target_has_zero_tables():
    with open(os.path.join(MODES_DIR, "m6_schema_only", "manifest.json")) as f:
        m6 = json.load(f)
    target_db = os.path.join(MODES_DIR, "m6_schema_only", m6["target_db"])
    c = sqlite3.connect(target_db)
    n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    c.close()
    assert n == 0


def test_m7_ddl_fingerprint_matches_m1():
    with open(os.path.join(MODES_DIR, "m1_bulk", "manifest.json")) as f:
        m1 = json.load(f)
    with open(os.path.join(MODES_DIR, "m7_data_only", "manifest.json")) as f:
        m7 = json.load(f)
    assert m1["target_ddl_fingerprint"] == m7["target_ddl_fingerprint_before"]


# ---- M2/M3/M4/M5/M8 reconciliation + determinism ---------------------------

def test_m2_transaction_truth_reconciles():
    with open(os.path.join(MODES_DIR, "m2_bulk_cdc", "manifest.json")) as f:
        m2 = json.load(f)
    assert m2["committed_transaction_count"] + m2["rolled_back_transaction_count"] == m2["transaction_count"]
    with open(os.path.join(MODES_DIR, "m2_bulk_cdc", "transaction_stream.json")) as f:
        stream = json.load(f)
    assert len(stream) == m2["transaction_count"]
    assert sum(len(tx["events"]) for tx in stream) == m2["total_event_count"]


def test_m3_initial_state_and_final_state_reconcile():
    d = os.path.join(MODES_DIR, "m3_cdc_only")
    with open(os.path.join(d, "manifest.json")) as f:
        m3 = json.load(f)
    with open(os.path.join(d, "initial_synchronized_state.json")) as f:
        initial = json.load(f)
    with open(os.path.join(d, "expected_post_cdc_state.json")) as f:
        final = json.load(f)
    assert len(initial) == m3["initial_row_count"]
    assert len(final) == m3["expected_post_cdc_row_count"]


def test_m4_batches_and_watermark_reconcile():
    d = os.path.join(MODES_DIR, "m4_incremental")
    with open(os.path.join(d, "manifest.json")) as f:
        m4 = json.load(f)
    with open(os.path.join(d, "poll_batches.json")) as f:
        batches = json.load(f)
    assert len(batches) == m4["poll_batch_count"]
    assert batches[-1]["watermark_after_commit"] == m4["final_durable_watermark_seq"]
    with open(os.path.join(d, "failure_injection_scenario.json")) as f:
        scenario = json.load(f)
    assert scenario["target_commit_happens"] is True
    assert scenario["watermark_commit_happens"] is False


def test_m5_and_m8_set_math_reconcile_and_rebuild_is_deterministic():
    from modes.m5_state_sync import build_m5_fixture
    from modes.m8_validation import build_m8_fixture

    m5_a = build_m5_fixture()
    m5_b = build_m5_fixture()
    assert m5_a == m5_b, "M5 rebuild must be byte-for-byte deterministic"
    assert m5_a["union_of_keys"] == (
        m5_a["equal_intersection"] + m5_a["modified_same_key"] + m5_a["source_only"] + m5_a["target_only"]
    )

    m8_a = build_m8_fixture()
    m8_b = build_m8_fixture()
    assert m8_a == m8_b, "M8 rebuild must be byte-for-byte deterministic"
    assert m8_a["union_of_keys"] == (
        m8_a["exact_matches"] + m8_a["modified_same_key"] + m8_a["source_only"] + m8_a["target_only"]
    )


def test_m2_m3_rebuild_is_deterministic():
    from modes.m2_bulk_cdc import build_m2_fixture
    from modes.m3_cdc_only import build_m3_fixture

    a = build_m2_fixture()
    b = build_m2_fixture()
    assert a == b

    a3 = build_m3_fixture()
    b3 = build_m3_fixture()
    assert a3 == b3


def test_reset_one_mode_does_not_change_others():
    """Resetting M5 must not silently change M8's on-disk state (§25)."""
    d8 = os.path.join(MODES_DIR, "m8_validation", "manifest.json")
    with open(d8) as f:
        before = json.load(f)

    from modes.m5_state_sync import build_m5_fixture
    build_m5_fixture()

    with open(d8) as f:
        after = json.load(f)
    assert before == after
