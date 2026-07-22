"""
Automated Architecture Conformance Test for Platform 8 Reporting Engine.

Asserts that no code in akaal/reporting/ imports internal engine or storage modules of other platforms directly.
"""

import ast
import glob
import os
import pytest

FORBIDDEN_PLATFORM_IMPORTS = [
    "akaal.workflow.engine",
    "akaal.workflow.execution",
    "akaal.schema.evolution_engine",
    "akaal.schema.compatibility",
    "akaal.cdc.coordinator",
    "akaal.cdc.sources",
    "akaal.streaming.engine",
    "akaal.api.rest",
    "akaal.api.grpc",
]


def test_enforce_platform8_boundary_isolation():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "akaal", "reporting"))
    py_files = glob.glob(os.path.join(root_dir, "**", "*.py"), recursive=True)

    assert len(py_files) > 0, "No akaal/reporting Python files found to inspect"

    violations = []

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
                    for bad in FORBIDDEN_PLATFORM_IMPORTS:
                        if alias.name.startswith(bad):
                            violations.append(f"Forbidden import '{alias.name}' in {filepath}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for bad in FORBIDDEN_PLATFORM_IMPORTS:
                        if node.module.startswith(bad):
                            violations.append(f"Forbidden import from '{node.module}' in {filepath}")

    assert len(violations) == 0, f"Platform 8 Boundary Isolation Violations:\n" + "\n".join(violations)
