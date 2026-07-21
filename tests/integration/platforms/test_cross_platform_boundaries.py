"""
Scenario 8 — Platform Boundary Strict Validation Test.
Verifies architectural isolation and strict boundaries between Platforms 1, 2, and 3.
"""

import inspect
import akaal.orchestration
import akaal.distributed
import akaal.streaming


def test_scenario_8_platform_boundary_isolation():
    # 1. Platform 1 Boundary Verification
    p1_modules = inspect.getmembers(akaal.orchestration, inspect.ismodule)
    p1_names = [m[0] for m in p1_modules]
    assert "scheduler" not in p1_names
    assert "streaming" not in p1_names

    # 2. Platform 2 Boundary Verification
    p2_modules = inspect.getmembers(akaal.distributed, inspect.ismodule)
    p2_names = [m[0] for m in p2_modules]
    assert "cdc" not in p2_names
    assert "ddl" not in p2_names
    assert "schema" not in p2_names

    # 3. Platform 3 Boundary Verification
    p3_modules = inspect.getmembers(akaal.streaming, inspect.ismodule)
    p3_names = [m[0] for m in p3_modules]
    assert "cdc" not in p3_names
    assert "migration" not in p3_names
    assert "adapters" not in p3_names
    assert "orchestration" not in p3_names

    print("\n--- Platform 1, 2, and 3 Strict Architectural Boundaries Verified ---")
