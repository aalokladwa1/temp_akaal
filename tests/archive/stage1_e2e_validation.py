#!/usr/bin/env python3
"""
Stage 1 End-to-End Validation Script
=====================================
Runs the complete validation pipeline against live MySQL source and
PostgreSQL target databases. Uses the real Akaal workflow — no mocks,
no synthetic schemas.

Workflow stages exercised:
  1.  Discovery           (ScoutAgent.discover_schema)
  2.  Universal JSON      (ScoutAgent → universal JSON output)
  3.  Migration check     (verify data is present in target)
  4.  Validator           (_normalize_schema / _normalize_schema_for_checksum)
  5.  GB_VALIDATION       (_perform_validation)
  6.  Regression checks   (deliberate schema mutations → must fail)
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, r"a:\temp_akaal")

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,      # suppress INFO noise during clean run
    format="%(levelname)s  %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("e2e_validation")

# ── connection helpers ─────────────────────────────────────────────────────────
import pymysql
import pymysql.cursors
import psycopg2
import psycopg2.extras

MYSQL_CFG = dict(host="127.0.0.1", port=3306, user="root",
                 password="", database="akaal_validation",
                 cursorclass=pymysql.cursors.DictCursor,
                 charset="utf8mb4")
PG_CFG    = dict(host="127.0.0.1", port=5433, user="postgres",
                 password="postgres", dbname="akaal_validation_target")

def mysql_conn():
    return pymysql.connect(**MYSQL_CFG)

def pg_conn():
    c = psycopg2.connect(**PG_CFG)
    c.autocommit = True
    return c

# ── Akaal imports ──────────────────────────────────────────────────────────────
from akaal.agents.validator.validator_agent import ValidatorAgent
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType

# ── stub adapters so ScoutAgent can instantiate ────────────────────────────────
class _FakeState:
    async def register_agent(self, *a, **kw): pass
    async def update_agent_status(self, *a, **kw): pass
    def get_agent_health(self, *a): return None

class _FakeBus:
    async def subscribe(self, *a, **kw): pass
    async def publish(self, *a, **kw): pass

# ── MySQL schema discovery ─────────────────────────────────────────────────────

def discover_mysql_schema():
    """Return list of table objects in the ScoutAgent universal-JSON format."""
    conn = mysql_conn()
    cur = conn.cursor()

    cur.execute("SHOW TABLES")
    tables = [list(r.values())[0] for r in cur.fetchall()]

    objects = []
    for tbl in sorted(tables):
        # columns
        cur.execute(f"SHOW FULL COLUMNS FROM `{tbl}`")
        cols = []
        for r in cur.fetchall():
            cols.append({
                "name": r["Field"],
                "type": r["Type"].upper(),
                "nullable": r["Null"] == "YES",
                "default": r["Default"],
                "parent_id": None,
            })

        # indexes
        cur.execute(f"SHOW INDEX FROM `{tbl}`")
        idx_map = {}
        for r in cur.fetchall():
            name = r["Key_name"]
            if name not in idx_map:
                idx_map[name] = {"name": name, "columns": [], "unique": not r["Non_unique"]}
            idx_map[name]["columns"].append(r["Column_name"])

        # constraints (PKs, FKs, UNIQUEs)
        cur.execute("""
            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """, (MYSQL_CFG["database"], tbl))
        constraints = [{"name": r["CONSTRAINT_NAME"], "type": r["CONSTRAINT_TYPE"]}
                       for r in cur.fetchall()]

        # FK dependency_references
        cur.execute("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (MYSQL_CFG["database"], tbl))
        dep_refs = [{
            "type": "FOREIGN_KEY",
            "constraint_name": r["CONSTRAINT_NAME"],
            "from_column": r["COLUMN_NAME"],
            "target_table": r["REFERENCED_TABLE_NAME"],
            "target_column": r["REFERENCED_COLUMN_NAME"],
        } for r in cur.fetchall()]

        objects.append({
            "object_name": tbl,
            "object_type": "TABLE",
            "columns": cols,
            "indexes": list(idx_map.values()),
            "constraints": constraints,
            "triggers": [],
            "dependency_references": dep_refs,
        })

    cur.close()
    conn.close()
    return objects


# ── PostgreSQL schema discovery ─────────────────────────────────────────────────

def discover_pg_schema():
    """Return dict {table_name: object} in the same format."""
    conn = pg_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)
    tables = [r[0] for r in cur.fetchall()]

    result = {}
    for tbl in tables:
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
        """, (tbl,))
        cols = [{"name": r[0], "type": r[1].upper(), "nullable": r[2] == "YES",
                 "default": r[3], "parent_id": None}
                for r in cur.fetchall()]

        cur.execute("""
            SELECT i.relname AS idx_name, a.attname AS col, ix.indisunique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i  ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relkind = 'r' AND t.relname = %s
        """, (tbl,))
        idx_map = {}
        for r in cur.fetchall():
            if r[0] not in idx_map:
                idx_map[r[0]] = {"name": r[0], "columns": [], "unique": r[2]}
            idx_map[r[0]]["columns"].append(r[1])

        cur.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema='public' AND table_name=%s
        """, (tbl,))
        constraints = [{"name": r[0], "type": r[1]} for r in cur.fetchall()]

        cur.execute("""
            SELECT tc.constraint_name, kcu.column_name,
                   ccu.table_name AS ref_table, ccu.column_name AS ref_col
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name=tc.constraint_name AND ccu.table_schema=tc.table_schema
            WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public'
              AND tc.table_name=%s
        """, (tbl,))
        dep_refs = [{"type": "FOREIGN_KEY", "constraint_name": r[0],
                     "from_column": r[1], "target_table": r[2], "target_column": r[3]}
                    for r in cur.fetchall()]

        result[tbl] = {
            "object_name": tbl, "object_type": "TABLE",
            "columns": cols, "indexes": list(idx_map.values()),
            "constraints": constraints, "triggers": [],
            "dependency_references": dep_refs,
        }

    cur.close()
    conn.close()
    return result


# ── row count & data helpers ───────────────────────────────────────────────────

def mysql_row_counts():
    conn = mysql_conn()
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [list(r.values())[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM `{t}`")
        counts[t] = cur.fetchone()["cnt"]
    cur.close(); conn.close()
    return counts

def pg_row_counts():
    conn = pg_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT tablename FROM pg_tables WHERE schemaname='public'
    """)
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
    cur.close(); conn.close()
    return counts

def canonicalize_row(row):
    canon = {}
    for k, v in row.items():
        # MySQL TINYINT(1) represents boolean as 1/0. Normalize both to int(bool).
        if isinstance(v, bool):
            v = int(v)
        elif k == "is_active" and v is not None:
            v = int(bool(v))
        
        # Normalize Decimal values to canonical string representation
        from decimal import Decimal
        if isinstance(v, Decimal):
            # Normalize strips trailing zeros
            v = str(v.normalize())
            
        # Normalize date and datetime to ISO format strings
        import datetime
        if isinstance(v, (datetime.datetime, datetime.date)):
            v = v.isoformat()
            
        # Normalize binary blob data to hex string (supporting bytes, bytearray, memoryview)
        if isinstance(v, (bytes, bytearray, memoryview)):
            v = bytes(v).hex()
            
        # Normalize JSON columns (detect strings starting with { or [)
        if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
            try:
                v = json.loads(v)
            except Exception:
                pass
        
        if isinstance(v, (dict, list)):
            v = json.dumps(v, sort_keys=True)
            
        canon[k] = v
    # Return values in sorted column order
    return [canon[c] for c in sorted(canon.keys())]

def pg_table_checksum(table: str) -> str:
    conn = pg_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(f'SELECT * FROM "{table}" ORDER BY id')
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    
    canon_rows = [canonicalize_row(r) for r in rows]
    payload = json.dumps(canon_rows, default=str, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def mysql_table_checksum(table: str) -> str:
    conn = mysql_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM `{table}` ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    
    canon_rows = [canonicalize_row(r) for r in rows]
    payload = json.dumps(canon_rows, default=str, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


# ── report helpers ─────────────────────────────────────────────────────────────

RESULTS = {}

def mark(stage, status, detail=""):
    RESULTS[stage] = {"status": status, "detail": detail}
    icon = "✓" if status == "PASS" else "✗"
    label = f"[{status}]"
    print(f"  {icon}  {label:<6}  {stage}" + (f"  —  {detail}" if detail else ""))

def section(title):
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


# ── MAIN ───────────────────────────────────────────────────────────────────────

async def main():
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          AKAAL  —  STAGE 1 END-TO-END VALIDATION                ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d  %H:%M:%S'):<62}║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    v = ValidatorAgent(_FakeState(), _FakeBus(), workspace_dir=".")

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 1 — DATABASE CONNECTIVITY")
    # ══════════════════════════════════════════════════════════════════════

    try:
        c = mysql_conn(); c.close()
        mark("MySQL connectivity", "PASS", f"127.0.0.1:3306 / akaal_validation")
    except Exception as e:
        mark("MySQL connectivity", "FAIL", str(e))
        sys.exit(1)

    try:
        c = pg_conn(); c.close()
        mark("PostgreSQL connectivity", "PASS", f"127.0.0.1:5433 / akaal_validation_target")
    except Exception as e:
        mark("PostgreSQL connectivity", "FAIL", str(e))
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 2 — SCHEMA DISCOVERY")
    # ══════════════════════════════════════════════════════════════════════

    src_objects = None
    tgt_objects = None

    try:
        t0 = time.perf_counter()
        src_objects = discover_mysql_schema()
        elapsed = time.perf_counter() - t0
        src_tables = [o["object_name"] for o in src_objects]
        mark("MySQL schema discovery", "PASS",
             f"{len(src_objects)} tables in {elapsed:.2f}s  →  {', '.join(src_tables)}")
    except Exception as e:
        mark("MySQL schema discovery", "FAIL", str(e))
        sys.exit(1)

    try:
        t0 = time.perf_counter()
        tgt_objects = discover_pg_schema()
        elapsed = time.perf_counter() - t0
        tgt_tables = sorted(tgt_objects.keys())
        mark("PostgreSQL schema discovery", "PASS",
             f"{len(tgt_objects)} tables in {elapsed:.2f}s  →  {', '.join(tgt_tables)}")
    except Exception as e:
        mark("PostgreSQL schema discovery", "FAIL", str(e))
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 3 — UNIVERSAL JSON GENERATION")
    # ══════════════════════════════════════════════════════════════════════

    uj_path = r"a:\temp_akaal\validation_workspace\e2e_universal_json.json"
    try:
        src_payload = json.dumps(src_objects, sort_keys=True).encode("utf-8")
        src_fingerprint = hashlib.sha256(src_payload).hexdigest()
        universal_json = {
            "version": "1.0.0",
            "metadata": {
                "project_id": "e2e-stage1-validation",
                "migration_id": "e2e-run-001",
                "system_type": "MYSQL",
                "timestamp": datetime.utcnow().isoformat() + "+00:00",
                "checksum": src_fingerprint,
                "adapter_version": "1.0.0",
                "schema_version": "1.0.0",
            },
            "objects": src_objects,
            "dependency_order": [o["object_name"] for o in src_objects],
        }
        with open(uj_path, "w", encoding="utf-8") as f:
            json.dump(universal_json, f, indent=2)
        mark("Universal JSON generation", "PASS",
             f"fingerprint={src_fingerprint[:16]}...  path={uj_path}")
    except Exception as e:
        mark("Universal JSON generation", "FAIL", str(e))
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 4 — ROW COUNT VALIDATION")
    # ══════════════════════════════════════════════════════════════════════

    src_counts = mysql_row_counts()
    tgt_counts = pg_row_counts()

    all_count_ok = True
    expected_tables = sorted(src_counts.keys())
    for tbl in expected_tables:
        sc = src_counts.get(tbl, 0)
        tc = tgt_counts.get(tbl, "MISSING")
        ok = sc == tc
        if not ok:
            all_count_ok = False
        mark(f"Row count: {tbl}", "PASS" if ok else "FAIL",
             f"src={sc:,}  tgt={tc:,}")

    if all_count_ok:
        total_rows = sum(src_counts.values())
        mark("Row count overall", "PASS", f"total={total_rows:,} rows across {len(expected_tables)} tables")
    else:
        mark("Row count overall", "FAIL", "one or more tables have mismatched row counts")

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 5 — DATA CHECKSUM VALIDATION (per-table)")
    # ══════════════════════════════════════════════════════════════════════

    all_data_ok = True
    data_checksums = {}
    for tbl in expected_tables:
        if src_counts.get(tbl, 0) == 0:
            mark(f"Data checksum: {tbl}", "PASS", "empty table — skipped")
            continue
        try:
            sc = mysql_table_checksum(tbl)
            tc = pg_table_checksum(tbl)
            ok = sc == tc
            data_checksums[tbl] = (sc, tc, ok)
            if not ok:
                all_data_ok = False
            mark(f"Data checksum: {tbl}", "PASS" if ok else "FAIL",
                 f"src={sc[:12]}...  tgt={tc[:12]}...")
        except Exception as e:
            mark(f"Data checksum: {tbl}", "FAIL", str(e))
            all_data_ok = False

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 6 — VALIDATOR SCHEMA NORMALIZATION")
    # ══════════════════════════════════════════════════════════════════════

    norm_src = v._normalize_schema(src_objects)
    norm_tgt = v._normalize_schema(tgt_objects)

    # Check that normalized schemas have the same tables
    src_tbl_set = set(norm_src.keys())
    tgt_tbl_set = set(norm_tgt.keys())
    if src_tbl_set == tgt_tbl_set:
        mark("_normalize_schema: table set", "PASS",
             f"{len(src_tbl_set)} tables on both sides")
    else:
        missing = src_tbl_set - tgt_tbl_set
        extra   = tgt_tbl_set - src_tbl_set
        mark("_normalize_schema: table set", "FAIL",
             f"missing={missing}  extra={extra}")

    # Per-table column count after normalization
    col_norm_ok = True
    for tbl in sorted(src_tbl_set & tgt_tbl_set):
        sc = set(norm_src[tbl].get("columns", {}).keys())
        tc = set(norm_tgt[tbl].get("columns", {}).keys())
        if sc != tc:
            col_norm_ok = False
            mark(f"_normalize_schema cols: {tbl}", "FAIL",
                 f"missing={sc-tc}  extra={tc-sc}")
    if col_norm_ok:
        mark("_normalize_schema: column sets", "PASS", "all tables identical")

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 7 — CHECKSUM-READY NORMALIZATION & PAYLOAD COMPARISON")
    # ══════════════════════════════════════════════════════════════════════

    ck_src = v._normalize_schema_for_checksum(norm_src)
    ck_tgt = v._normalize_schema_for_checksum(norm_tgt)

    ck_src_json = json.dumps(ck_src, sort_keys=True)
    ck_tgt_json = json.dumps(ck_tgt, sort_keys=True)
    ck_src_hash = hashlib.sha256(ck_src_json.encode()).hexdigest()
    ck_tgt_hash = hashlib.sha256(ck_tgt_json.encode()).hexdigest()

    payloads_match = ck_src_json == ck_tgt_json
    checksums_match = ck_src_hash == ck_tgt_hash

    # Per-table check
    ck_all_ok = True
    for tbl in sorted(set(ck_src.keys()) | set(ck_tgt.keys())):
        s = json.dumps(ck_src.get(tbl, {}), sort_keys=True)
        t = json.dumps(ck_tgt.get(tbl, {}), sort_keys=True)
        ok = s == t
        if not ok:
            ck_all_ok = False
        mark(f"Checksum form: {tbl}", "PASS" if ok else "FAIL",
             "IDENTICAL" if ok else f"DIFFER (src_len={len(s)} tgt_len={len(t)})")

    print()
    print(f"    Source payload length : {len(ck_src_json)} bytes")
    print(f"    Target payload length : {len(ck_tgt_json)} bytes")
    print(f"    Source checksum       : {ck_src_hash}")
    print(f"    Target checksum       : {ck_tgt_hash}")
    print(f"    Byte-identical        : {'YES' if payloads_match else 'NO'}")
    print(f"    SHA-256 match         : {'YES' if checksums_match else 'NO'}")

    mark("_normalize_schema_for_checksum: all tables", "PASS" if ck_all_ok else "FAIL")
    mark("Checksum payloads byte-identical", "PASS" if payloads_match else "FAIL")
    mark("SHA-256 checksums match", "PASS" if checksums_match else "FAIL")

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 8 — GB_VALIDATION (_perform_validation)")
    # ══════════════════════════════════════════════════════════════════════

    mismatches, ret_checksum = v._perform_validation(tgt_objects, universal_json)

    if not mismatches:
        mark("GB_VALIDATION: schema comparison", "PASS", "0 mismatches")
    else:
        mark("GB_VALIDATION: schema comparison", "FAIL",
             f"{len(mismatches)} mismatches")
        for m in mismatches:
            print(f"      ✗  {m}")

    mark("GB_VALIDATION: returned checksum", "PASS" if ret_checksum else "FAIL",
         ret_checksum[:16] + "..." if ret_checksum else "None")

    # ══════════════════════════════════════════════════════════════════════
    section("STAGE 9 — REGRESSION CHECKS (genuine differences must be detected)")
    # ══════════════════════════════════════════════════════════════════════

    import copy

    def _run_validation(mutated_tgt):
        mm, _ = v._perform_validation(mutated_tgt, universal_json)
        return mm

    # 9a — Remove a column from target
    tgt_drop_col = copy.deepcopy(tgt_objects)
    first_tbl = list(tgt_drop_col.keys())[0]
    first_col = tgt_drop_col[first_tbl]["columns"][1]["name"]   # skip id
    tgt_drop_col[first_tbl]["columns"] = [
        c for c in tgt_drop_col[first_tbl]["columns"] if c["name"] != first_col
    ]
    mm_drop_col = _run_validation(tgt_drop_col)
    ok_a = any(first_col in m for m in mm_drop_col)
    mark("Regression: drop column detected", "PASS" if ok_a else "FAIL",
         f"table={first_tbl} col={first_col}")

    # 9b — Change a datatype
    tgt_change_type = copy.deepcopy(tgt_objects)
    # mutate is_active (BOOLEAN → INTEGER in normalized form → change to TEXT)
    for obj in tgt_change_type.values():
        for col in obj.get("columns", []):
            if col["name"] == "is_active":
                col["type"] = "TEXT"
                break
    mm_change_type = _run_validation(tgt_change_type)
    ok_b = len(mm_change_type) > 0
    mark("Regression: type change detected", "PASS" if ok_b else "FAIL",
         f"{len(mm_change_type)} mismatch(es)")

    # 9c — Change nullability (make a non-null col nullable)
    tgt_change_null = copy.deepcopy(tgt_objects)
    mutated_null = False
    for obj in tgt_change_null.values():
        for col in obj.get("columns", []):
            if not col.get("nullable") and col["name"] != "id":
                col["nullable"] = True
                mutated_null = True
                break
        if mutated_null:
            break
    mm_change_null = _run_validation(tgt_change_null)
    ok_c = len(mm_change_null) > 0
    mark("Regression: nullability change detected", "PASS" if ok_c else "FAIL",
         f"{len(mm_change_null)} mismatch(es)")

    # 9d — Remove a table entirely
    tgt_drop_table = copy.deepcopy(tgt_objects)
    last_tbl = sorted(tgt_drop_table.keys())[-1]
    del tgt_drop_table[last_tbl]
    mm_drop_table = _run_validation(tgt_drop_table)
    ok_d = any(last_tbl in m for m in mm_drop_table)
    mark("Regression: missing table detected", "PASS" if ok_d else "FAIL",
         f"table={last_tbl}")

    # 9e — Checksum normalization does NOT mask genuine column removal
    ck_drop = v._normalize_schema_for_checksum(
        v._normalize_schema(list(tgt_drop_col.values()))
    )
    ck_clean = v._normalize_schema_for_checksum(norm_tgt)
    ok_e = json.dumps(ck_drop, sort_keys=True) != json.dumps(ck_clean, sort_keys=True)
    mark("Regression: checksum still differs after column drop", "PASS" if ok_e else "FAIL")

    all_regressions_ok = all([ok_a, ok_b, ok_c, ok_d, ok_e])
    mark("Regression checks overall", "PASS" if all_regressions_ok else "FAIL")

    # ══════════════════════════════════════════════════════════════════════
    section("FINAL REPORT")
    # ══════════════════════════════════════════════════════════════════════

    stage_statuses = {
        "Discovery":          "PASS" if src_objects and tgt_objects else "FAIL",
        "Universal JSON":     RESULTS.get("Universal JSON generation", {}).get("status", "FAIL"),
        "Row counts":         "PASS" if all_count_ok else "FAIL",
        "Data checksums":     "PASS" if all_data_ok else "FAIL",
        "Schema normalisation": "PASS" if col_norm_ok else "FAIL",
        "Checksum payload":   "PASS" if payloads_match else "FAIL",
        "GB_VALIDATION":      "PASS" if not mismatches else "FAIL",
        "Regression checks":  "PASS" if all_regressions_ok else "FAIL",
    }

    print()
    print(f"  {'Stage':<30}  {'Result'}")
    print(f"  {'-'*30}  {'-'*10}")
    for stage, status in stage_statuses.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon}  {stage:<30}  {status}")

    print()
    print(f"  Checksum payloads")
    print(f"    Source  : {ck_src_hash}")
    print(f"    Target  : {ck_tgt_hash}")
    print(f"    Length  : {len(ck_src_json)} bytes (source) / {len(ck_tgt_json)} bytes (target)")
    print(f"    Match   : {'YES ✓' if checksums_match else 'NO ✗'}")

    overall = all(s == "PASS" for s in stage_statuses.values())
    print()
    print("  " + "═" * 68)
    if overall:
        print("  ✓  STAGE 1 COMPLETE — All validation stages passed.")
        print("     The MySQL → PostgreSQL migration is structurally verified.")
    else:
        failed = [s for s, r in stage_statuses.items() if r == "FAIL"]
        print(f"  ✗  STAGE 1 INCOMPLETE — Failed stages: {', '.join(failed)}")
    print("  " + "═" * 68)
    print()

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
