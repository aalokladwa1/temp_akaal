"""M1 fixture: complete finite bulk migration (build-spec §14).

Source truth = the full 1,000,000-row baseline (data/source_baseline.sqlite,
already built and independently manifested by manifests/source_manifest.py).
Target truth = an empty schema shell with identical DDL, zero rows -- what
a bulk migration target looks like before M1 executes.
"""
from __future__ import annotations

import os

from modes._common import mode_dir, build_empty_schema_shell, write_json, DATA_DIR


def build_m1_fixture() -> dict:
    d = mode_dir("m1_bulk")
    target_db = os.path.join(d, "target_shell.sqlite")
    ddl_fingerprint = build_empty_schema_shell(target_db)

    manifest = {
        "mode": "M1",
        "description": "complete finite bulk migration",
        "source_db": os.path.relpath(os.path.join(DATA_DIR, "source_baseline.sqlite"), d),
        "source_manifest": os.path.relpath(os.path.join(DATA_DIR, "source_manifest.json"), d),
        "target_db": os.path.basename(target_db),
        "target_initial_row_count": 0,
        "target_ddl_fingerprint": ddl_fingerprint,
        "expected_final_target_row_count": 1_000_000,
        "reset_instructions": "rerun tests.fixtures.estate.modes.m1_bulk:build_m1_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    m = build_m1_fixture()
    print(m)
