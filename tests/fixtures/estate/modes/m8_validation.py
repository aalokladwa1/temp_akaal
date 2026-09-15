"""M8 fixture: validation/reconciliation only (build-spec §21).

A bounded, deliberately discrepant source/target set covering every
required difference category. M8 must never repair anything -- this
fixture is deliberately left discrepant, with an independent mismatch
manifest whose mathematics is asserted to reconcile before being written.
"""
from __future__ import annotations

import os

from modes._common import mode_dir, write_json


def build_m8_fixture() -> dict:
    d = mode_dir("m8_validation")

    source = {}
    target = {}

    # exact matches (150)
    for i in range(1, 151):
        row = {"amount": i * 1.5, "label": f"item-{i}", "flag": i % 2}
        source[f"R{i:05d}"] = dict(row)
        target[f"R{i:05d}"] = dict(row)

    # source-only (35), target-only (25)
    for i in range(151, 186):
        source[f"R{i:05d}"] = {"amount": i, "label": f"src-only-{i}", "flag": 0}
    for i in range(186, 211):
        target[f"R{i:05d}"] = {"amount": i, "label": f"tgt-only-{i}", "flag": 0}

    categories = {
        "null_diff": lambda j: ({"amount": j, "label": None, "flag": 0}, {"amount": j, "label": "was-null", "flag": 0}),
        "unicode_diff": lambda j: ({"amount": j, "label": "Zürich", "flag": 0}, {"amount": j, "label": "Zurich", "flag": 0}),
        "whitespace_diff": lambda j: ({"amount": j, "label": "value  ", "flag": 0}, {"amount": j, "label": "value", "flag": 0}),
        "case_diff": lambda j: ({"amount": j, "label": "ABC", "flag": 0}, {"amount": j, "label": "abc", "flag": 0}),
        "numeric_diff": lambda j: ({"amount": j + 0.001, "label": "n", "flag": 0}, {"amount": j, "label": "n", "flag": 0}),
        "precision_diff": lambda j: ({"amount": round(j + 1 / 3, 6), "label": "p", "flag": 0}, {"amount": round(j + 1 / 3, 2), "label": "p", "flag": 0}),
        "timestamp_diff": lambda j: ({"amount": j, "label": "2024-06-01T00:00:00.000001", "flag": 0}, {"amount": j, "label": "2024-06-01T00:00:00.000000", "flag": 0}),
        "binary_diff": lambda j: ({"amount": j, "label": "0xDEADBEEF", "flag": 0}, {"amount": j, "label": "0xDEADBEEE", "flag": 0}),
        "clob_diff": lambda j: ({"amount": j, "label": "x" * 50, "flag": 0}, {"amount": j, "label": "x" * 49 + "y", "flag": 0}),
        "structural_diff": lambda j: ({"amount": j, "label": "s", "flag": 0, "extra_col": "present_in_source_only"}, {"amount": j, "label": "s", "flag": 0}),
    }

    base = 300
    per_category = 10
    category_key_map = {}
    for ci, (cat_name, make_pair) in enumerate(categories.items()):
        keys = []
        for j in range(per_category):
            key = f"R{base + ci * per_category + j:05d}"
            s_row, t_row = make_pair(j)
            source[key] = s_row
            target[key] = t_row
            keys.append(key)
        category_key_map[cat_name] = keys

    source_keys = set(source.keys())
    target_keys = set(target.keys())
    exact_matches = {k for k in (source_keys & target_keys) if source[k] == target[k]}
    modified = {k for k in (source_keys & target_keys) if source[k] != target[k]}
    source_only = source_keys - target_keys
    target_only = target_keys - source_keys
    union_keys = source_keys | target_keys

    reconciliation = {
        "source_physical_rows": len(source_keys),
        "target_physical_rows": len(target_keys),
        "exact_matches": len(exact_matches),
        "source_only": len(source_only),
        "target_only": len(target_only),
        "modified_same_key": len(modified),
        "union_of_keys": len(union_keys),
        "expected_discrepancy_total": len(modified) + len(source_only) + len(target_only),
    }
    assert reconciliation["union_of_keys"] == (
        reconciliation["exact_matches"] + reconciliation["modified_same_key"]
        + reconciliation["source_only"] + reconciliation["target_only"]
    ), "M8 mismatch mathematics must reconcile exactly"

    mismatch_manifest = {
        "modified_keys_by_category": category_key_map,
        "source_only_keys": sorted(source_only),
        "target_only_keys": sorted(target_only),
    }

    write_json(os.path.join(d, "source_set.json"), source)
    write_json(os.path.join(d, "target_set.json"), target)
    write_json(os.path.join(d, "mismatch_manifest.json"), mismatch_manifest)

    manifest = {
        "mode": "M8",
        "description": "validation/reconciliation-only discrepancy set (deliberately left unrepaired)",
        **reconciliation,
        "discrepancy_categories": list(categories.keys()),
        "invariant": "M8 must never mutate source or target; this fixture stays discrepant across reset",
        "reset_instructions": "rerun tests.fixtures.estate.modes.m8_validation:build_m8_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    print(build_m8_fixture())
