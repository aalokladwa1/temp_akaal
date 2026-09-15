"""Deterministic reset/rebuild tooling (build-spec §26).

Every builder in this package is already idempotent (removes its own
output before regenerating), so "reset" is simply "call the builder again"
-- verified by the self-test suite, which rebuilds and checks fingerprints
reproduce exactly.
"""
from __future__ import annotations

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MODE_BUILDERS = {}


def _lazy_builders():
    if MODE_BUILDERS:
        return MODE_BUILDERS
    from modes.m1_bulk import build_m1_fixture
    from modes.m2_bulk_cdc import build_m2_fixture
    from modes.m3_cdc_only import build_m3_fixture
    from modes.m4_incremental import build_m4_fixture
    from modes.m5_state_sync import build_m5_fixture
    from modes.m6_schema_only import build_m6_fixture
    from modes.m7_data_only import build_m7_fixture
    from modes.m8_validation import build_m8_fixture
    MODE_BUILDERS.update({
        "M1": build_m1_fixture, "M2": build_m2_fixture, "M3": build_m3_fixture,
        "M4": build_m4_fixture, "M5": build_m5_fixture, "M6": build_m6_fixture,
        "M7": build_m7_fixture, "M8": build_m8_fixture,
    })
    return MODE_BUILDERS


def rebuild_baseline():
    from build_estate import build_baseline_phase
    return build_baseline_phase()


def rebuild_source_manifest():
    from manifests.source_manifest import build_source_manifest
    return build_source_manifest()


def reset_mode(mode: str):
    builders = _lazy_builders()
    if mode not in builders:
        raise ValueError(f"unknown mode {mode}, expected one of {sorted(builders)}")
    return builders[mode]()


def reset_all(include_baseline: bool = False):
    results = {}
    if include_baseline:
        results["baseline"] = rebuild_baseline()
        results["source_manifest"] = rebuild_source_manifest()
    for mode in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"):
        results[mode] = reset_mode(mode)
    return results


def restore_plsql_corpus():
    """The PL/SQL corpus is pure Python data (plsql_corpus/*.py) -- it has
    no separate physical state to reset; re-importing it always reproduces
    the same objects. Returns the object count as a reset-verification
    signal."""
    from plsql_corpus.expected_truth import ALL_OBJECTS
    return {"object_count": len(ALL_OBJECTS)}


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action == "all":
        print(reset_all(include_baseline=False))
    elif action == "baseline":
        print(rebuild_baseline())
    elif action in _lazy_builders():
        print(reset_mode(action))
    else:
        raise SystemExit(f"unknown action {action}")
