"""Independent source-of-truth manifest, extracted from the physically built
source_baseline.sqlite (not copy-pasted from config/domains.py) -- build-spec §27.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from generator.schema_builder import physical_table_name
from config.domains import ALL_TABLES, SCHEMA_TARGETS
from manifests.fingerprint import table_fingerprint, estate_fingerprint

DATA_DIR = os.path.join(HERE, "data")
BASELINE_DB = os.path.join(DATA_DIR, "source_baseline.sqlite")


def build_source_manifest(fingerprint_tables: bool = True) -> dict:
    conn = sqlite3.connect(BASELINE_DB)
    conn.row_factory = None

    lob_hashes_path = os.path.join(DATA_DIR, "lob_hashes.json")
    lob_hashes = {}
    if os.path.exists(lob_hashes_path):
        with open(lob_hashes_path, "r", encoding="utf-8") as f:
            lob_hashes = json.load(f)

    tables_manifest = {}
    fingerprints = {}
    schema_row_totals = {}
    t0 = time.time()

    for spec in ALL_TABLES:
        phys = physical_table_name(spec.schema, spec.name)
        row_count = conn.execute(f'SELECT COUNT(*) FROM "{phys}"').fetchone()[0]
        schema_row_totals[spec.schema] = schema_row_totals.get(spec.schema, 0) + row_count

        col_info = conn.execute(f'PRAGMA table_info("{phys}")').fetchall()
        fk_info = conn.execute(f'PRAGMA foreign_key_list("{phys}")').fetchall()

        entry = {
            "schema": spec.schema,
            "table": spec.name,
            "physical_table": phys,
            "row_count": row_count,
            "declared_row_count": spec.row_count,
            "column_count": len(col_info),
            "columns": [{"name": c[1], "sqlite_type": c[2], "not_null": bool(c[3])} for c in col_info],
            "primary_key": list(spec.primary_key) if spec.primary_key else None,
            "pk_style": spec.pk_style.value,
            "foreign_key_count": len(fk_info),
            "unique_constraint_count": len(spec.unique_constraints),
            "kind": spec.kind.value,
        }
        tables_manifest[spec.qualified_name] = entry

        if fingerprint_tables:
            fingerprints[phys] = table_fingerprint(conn, phys)

    conn.close()

    lob_summary = {
        band: {
            "count": len(entries),
            "total_bytes": sum(e["byte_length"] for e in entries),
        }
        for band, entries in lob_hashes.items()
    }

    manifest = {
        "schema_count": len(SCHEMA_TARGETS),
        "schema_targets": SCHEMA_TARGETS,
        "schema_row_totals_declared": {s: sum(t.row_count for t in ALL_TABLES if t.schema == s) for s in SCHEMA_TARGETS},
        "schema_row_totals_physical": schema_row_totals,
        "table_count": len(ALL_TABLES),
        "populated_table_count": sum(1 for t in ALL_TABLES if t.row_count > 0),
        "empty_table_count": sum(1 for t in ALL_TABLES if t.row_count == 0),
        "no_pk_table_count": sum(1 for t in ALL_TABLES if t.primary_key is None),
        "total_rows_declared": sum(t.row_count for t in ALL_TABLES),
        "total_rows_physical": sum(schema_row_totals.values()),
        "tables": tables_manifest,
        "lob_estate_summary": lob_summary,
        "table_fingerprints": fingerprints,
        "build_time_seconds": time.time() - t0,
    }
    manifest["estate_fingerprint"] = estate_fingerprint(fingerprints) if fingerprints else None
    return manifest


if __name__ == "__main__":
    m = build_source_manifest()
    out = os.path.join(DATA_DIR, "source_manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, default=str)
    print("schema_count", m["schema_count"])
    print("table_count", m["table_count"])
    print("total_rows_physical", m["total_rows_physical"])
    print("total_rows_declared", m["total_rows_declared"])
    print("estate_fingerprint", m["estate_fingerprint"])
    print("build_time_seconds", m["build_time_seconds"])
