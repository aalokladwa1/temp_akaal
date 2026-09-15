"""Orchestration entrypoint for the simulated 1,000,000-row AKAAL estate.

Usage (from repo root):
    .venv/Scripts/python.exe -m tests.fixtures.estate.build_estate baseline

Phases are added incrementally; `baseline` builds source_baseline.sqlite.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

DATA_DIR = os.path.join(HERE, "data")
BASELINE_DB = os.path.join(DATA_DIR, "source_baseline.sqlite")


def build_baseline_phase():
    from generator.schema_builder import build_schema
    from generator.baseline_loader import build_baseline
    from config.domains import ALL_TABLES

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(BASELINE_DB):
        os.remove(BASELINE_DB)
    for ext in ("-wal", "-shm"):
        p = BASELINE_DB + ext
        if os.path.exists(p):
            os.remove(p)

    conn = sqlite3.connect(BASELINE_DB)
    t0 = time.time()
    build_schema(conn, ALL_TABLES)

    def progress(name, n):
        elapsed = time.time() - t0
        print(f"[{elapsed:7.1f}s] {name}: {n} rows", flush=True)

    stats = build_baseline(conn, tables=ALL_TABLES, progress=progress)
    elapsed = time.time() - t0

    conn.execute("PRAGMA foreign_keys = ON;")
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.commit()
    conn.close()

    lob_hashes_out = os.path.join(DATA_DIR, "lob_hashes.json")
    with open(lob_hashes_out, "w", encoding="utf-8") as f:
        json.dump(stats["lob_hashes"], f)

    disk_bytes = os.path.getsize(BASELINE_DB)
    summary = {
        "elapsed_seconds": elapsed,
        "total_rows": stats["total_rows"],
        "table_count": len(stats["tables"]),
        "lob_band_counts": stats["lob_band_counts"],
        "fk_violations": len(violations),
        "disk_bytes": disk_bytes,
    }
    with open(os.path.join(DATA_DIR, "baseline_build_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("BASELINE BUILD SUMMARY:", json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if phase == "baseline":
        build_baseline_phase()
    else:
        raise SystemExit(f"unknown phase: {phase}")
