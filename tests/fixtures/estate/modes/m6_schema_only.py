"""M6 fixture: schema-only migration, no data transport (build-spec §19).

Source truth = the full object corpus: 206-table relational schema
(config/domains.py) + the PL/SQL corpus (plsql_corpus/). Target begins as a
completely empty database (no tables at all) -- M6 must be testable without
ever transporting source row data.
"""
from __future__ import annotations

import os
import sqlite3

from modes._common import mode_dir, write_json, DATA_DIR
from config.domains import ALL_TABLES
from plsql_corpus.expected_truth import EXPECTED_TRUTH, ALL_OBJECTS


def build_m6_fixture() -> dict:
    d = mode_dir("m6_schema_only")
    target_db = os.path.join(d, "target_empty.sqlite")
    if os.path.exists(target_db):
        os.remove(target_db)
    conn = sqlite3.connect(target_db)  # intentionally left with zero tables
    conn.close()

    object_manifest = {
        "relational_object_count": len(ALL_TABLES),
        "plsql_object_count": len(ALL_OBJECTS),
        "plsql_object_kinds": sorted(set(o.kind for o in ALL_OBJECTS)),
    }
    write_json(os.path.join(d, "plsql_expected_truth.json"), EXPECTED_TRUTH)

    manifest = {
        "mode": "M6",
        "description": "schema-only migration (DDL only, no data transport)",
        "source_schema_manifest": os.path.relpath(os.path.join(DATA_DIR, "source_manifest.json"), d),
        "target_db": os.path.basename(target_db),
        "target_initial_table_count": 0,
        "object_manifest": object_manifest,
        "invariant": "target must gain schema/objects but must never gain source row data under M6",
        "reset_instructions": "rerun tests.fixtures.estate.modes.m6_schema_only:build_m6_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    m = build_m6_fixture()
    print(m)
