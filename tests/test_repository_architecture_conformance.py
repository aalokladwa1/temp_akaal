"""
Global Repository-Wide Architecture Conformance Test Suite.

Asserts that no platform package directly imports internal implementations from other platforms.
Cross-platform interactions MUST route exclusively through public facade interfaces.
"""

import ast
import glob
import os
import pytest

PLATFORM_BOUNDARIES = {
    "akaal/api": [
        "akaal.workflow.engine",
        "akaal.schema.evolution_engine",
        "akaal.cdc.coordinator",
        "akaal.reporting.engine",
    ],
    "akaal/cdc": [
        "akaal.workflow.engine",
        "akaal.schema.evolution_engine",
        "akaal.streaming.engine",
        "akaal.api.rest",
        "akaal.api.grpc",
    ],
    "akaal/reporting": [
        "akaal.workflow.engine",
        "akaal.schema.evolution_engine",
        "akaal.cdc.coordinator",
        "akaal.streaming.engine",
        "akaal.api.rest",
        "akaal.api.grpc",
    ],
}


def test_enforce_global_architecture_boundaries():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    violations = []

    for platform_path, forbidden_list in PLATFORM_BOUNDARIES.items():
        dir_path = os.path.join(repo_root, platform_path)
        if not os.path.exists(dir_path):
            continue

        py_files = glob.glob(os.path.join(dir_path, "**", "*.py"), recursive=True)

        for filepath in py_files:
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=filepath)
                except SyntaxError as e:
                    violations.append(f"Syntax error in {filepath}: {str(e)}")
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for bad in forbidden_list:
                            if alias.name.startswith(bad):
                                violations.append(f"Forbidden import '{alias.name}' in {filepath}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for bad in forbidden_list:
                            if node.module.startswith(bad):
                                violations.append(f"Forbidden import from '{node.module}' in {filepath}")

    assert len(violations) == 0, f"Global Architecture Boundary Violations:\n" + "\n".join(violations)
