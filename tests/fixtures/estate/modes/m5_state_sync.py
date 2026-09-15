"""M5 fixture: state-based synchronization (build-spec §18).

A bounded, mathematically explicit source/target key set covering every
required difference category. Every number below is independently
recomputed from the constructed dicts (not hand-typed), and the module
asserts the set-math reconciles exactly before returning.
"""
from __future__ import annotations

import os

from modes._common import mode_dir, write_json


def build_m5_fixture() -> dict:
    d = mode_dir("m5_state_sync")

    source = {}
    target = {}

    # equal rows (100)
    for i in range(1, 101):
        row = {"val": i, "note": f"equal-{i}"}
        source[f"K{i:05d}"] = dict(row)
        target[f"K{i:05d}"] = dict(row)

    # source-only rows (40)
    for i in range(101, 141):
        source[f"K{i:05d}"] = {"val": i, "note": f"source-only-{i}"}

    # target-only rows (30)
    for i in range(141, 171):
        target[f"K{i:05d}"] = {"val": i, "note": f"target-only-{i}"}

    # modified same-key rows, one sub-case per difference category (60 total)
    modified_categories = ["null_diff", "unicode_diff", "numeric_diff", "timestamp_diff", "binary_diff_hexlen"]
    base = 171
    for ci, category in enumerate(modified_categories):
        for j in range(12):
            key = f"K{base + ci * 12 + j:05d}"
            if category == "null_diff":
                source[key] = {"val": j, "note": None}
                target[key] = {"val": j, "note": "was-null-now-set"}
            elif category == "unicode_diff":
                source[key] = {"val": j, "note": "café"}
                target[key] = {"val": j, "note": "cafe"}
            elif category == "numeric_diff":
                source[key] = {"val": j, "note": "n"}
                target[key] = {"val": j + 0.01, "note": "n"}
            elif category == "timestamp_diff":
                source[key] = {"val": j, "note": "2024-01-01T00:00:00"}
                target[key] = {"val": j, "note": "2024-01-01T00:00:01"}
            elif category == "binary_diff_hexlen":
                source[key] = {"val": j, "note": "deadbeef"}
                target[key] = {"val": j, "note": "deadbeefcafe"}

    source_keys = set(source.keys())
    target_keys = set(target.keys())
    equal_keys = {k for k in (source_keys & target_keys) if source[k] == target[k]}
    modified_keys = {k for k in (source_keys & target_keys) if source[k] != target[k]}
    source_only_keys = source_keys - target_keys
    target_only_keys = target_keys - source_keys
    union_keys = source_keys | target_keys

    assert len(equal_keys) + len(modified_keys) == len(source_keys & target_keys)
    assert len(union_keys) == len(equal_keys) + len(modified_keys) + len(source_only_keys) + len(target_only_keys)

    reconciliation = {
        "source_physical_rows": len(source_keys),
        "target_physical_rows": len(target_keys),
        "equal_intersection": len(equal_keys),
        "modified_same_key": len(modified_keys),
        "source_only": len(source_only_keys),
        "target_only": len(target_only_keys),
        "union_of_keys": len(union_keys),
        "expected_delta_count": len(modified_keys) + len(source_only_keys) + len(target_only_keys),
    }
    assert reconciliation["union_of_keys"] == (
        reconciliation["equal_intersection"] + reconciliation["modified_same_key"]
        + reconciliation["source_only"] + reconciliation["target_only"]
    ), "M5 set-math must reconcile exactly"

    write_json(os.path.join(d, "source_set.json"), source)
    write_json(os.path.join(d, "target_set.json"), target)
    write_json(os.path.join(d, "delta_manifest.json"), {
        "modified_keys": sorted(modified_keys),
        "source_only_keys": sorted(source_only_keys),
        "target_only_keys": sorted(target_only_keys),
        "modified_categories": modified_categories,
    })

    manifest = {
        "mode": "M5",
        "description": "state-based synchronization delta set with exact set-math reconciliation",
        **reconciliation,
        "reset_instructions": "rerun tests.fixtures.estate.modes.m5_state_sync:build_m5_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    print(build_m5_fixture())
