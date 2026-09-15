"""M7 fixture: data-only migration into a pre-existing target schema (build-spec §20).

Target begins with the correct DDL already applied (as if a separate DBA
process pre-created it) and zero rows. Source data truth = the full
1,000,000-row baseline. A DDL fingerprint is recorded before any M7 work so
a later test can prove AKAAL did not execute schema DDL during M7.
"""
from __future__ import annotations

import os

from modes._common import mode_dir, build_empty_schema_shell, write_json, DATA_DIR


def build_m7_fixture() -> dict:
    d = mode_dir("m7_data_only")
    target_db = os.path.join(d, "target_precreated.sqlite")
    ddl_fingerprint = build_empty_schema_shell(target_db)

    manifest = {
        "mode": "M7",
        "description": "data-only migration into pre-created target structures",
        "target_db": os.path.basename(target_db),
        "target_ddl_fingerprint_before": ddl_fingerprint,
        "source_db": os.path.relpath(os.path.join(DATA_DIR, "source_baseline.sqlite"), d),
        "source_manifest": os.path.relpath(os.path.join(DATA_DIR, "source_manifest.json"), d),
        "expected_final_target_row_count": 1_000_000,
        "invariant": "target_ddl_fingerprint_after M7 completes must equal target_ddl_fingerprint_before "
                      "(AKAAL must not execute DDL under M7)",
        "reset_instructions": "rerun tests.fixtures.estate.modes.m7_data_only:build_m7_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    m = build_m7_fixture()
    print(m)
