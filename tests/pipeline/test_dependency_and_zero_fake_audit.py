"""tests/pipeline/test_dependency_and_zero_fake_audit.py
======================================================
Automated static AST dependency & zero-fake audit over 100% of production files in akaalPipeline/.
"""

from __future__ import annotations

import ast
import os
import pytest

FORBIDDEN_PRODUCTION_PATTERNS = [
    "mock",
    "fake",
    "dummy",
    "placeholder",
    "simulated",
    "canned_success",
    "hardcoded_success",
    "notimplementederror",
]

FORBIDDEN_IMPORTS = [
    "akaal.engine",
    "akaal.gateway",
    "EngineGateway",
    "AkaalSuperEngine",
    "akaal.connectors",
    "akaal.cdc",
    "akaal.validation",
    "tauri",
    "react",
]


def test_zero_fake_production_audit():
    """Scan 100% of production files in akaalPipeline/ for forbidden fake/mock markers."""
    production_files = []
    for root, _, files in os.walk("akaalPipeline"):
        for file in files:
            if file.endswith(".py"):
                production_files.append(os.path.join(root, file))

    assert len(production_files) >= 30, f"Expected at least 30 production files, found {len(production_files)}"

    violations = []
    for path in production_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            lower_content = content.lower()
            for pattern in FORBIDDEN_PRODUCTION_PATTERNS:
                if pattern in lower_content:
                    violations.append(f"{path}: contains forbidden marker {pattern!r}")

    assert not violations, f"Zero-fake production audit failed:\n" + "\n".join(violations)


def test_dependency_audit_no_forbidden_imports():
    """Scan 100% of production files in akaalPipeline/ to ensure zero legacy or UI imports."""
    production_files = []
    for root, _, files in os.walk("akaalPipeline"):
        for file in files:
            if file.endswith(".py"):
                production_files.append(os.path.join(root, file))

    violations = []
    for path in production_files:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in FORBIDDEN_IMPORTS:
                            if forbidden in alias.name:
                                violations.append(f"{path}: imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in FORBIDDEN_IMPORTS:
                            if forbidden in node.module:
                                violations.append(f"{path}: imports from {node.module}")

    assert not violations, f"Dependency audit failed:\n" + "\n".join(violations)
