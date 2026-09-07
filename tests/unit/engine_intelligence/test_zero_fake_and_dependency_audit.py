"""tests/unit/engine_intelligence/test_zero_fake_and_dependency_audit.py
==========================================================================
Automated static AST dependency & zero-fake audit over 100% of production files
in akaalEngine/intelligence/ (P7C.1). Mirrors the audit discipline already
established by tests/pipeline/test_dependency_and_zero_fake_audit.py and
tests/ipc/test_dependency_audit.py -- a twin test scoped to the new package
rather than widening those existing audits' scope (which cover different
directories with their own forbidden-import lists appropriate to their layer).
"""

from __future__ import annotations

import ast
import os

FORBIDDEN_PRODUCTION_PATTERNS = [
    "mock",
    "fake",
    "dummy",
    "placeholder",
    "simulated",
    "canned_success",
    "hardcoded_success",
    "notimplementederror",
    "todo:",
    "fixme:",
]

# akaalEngine must never depend on akaalPipeline or akaalIPC -- the dependency
# runs the other way (akaalPipeline/akaalIPC consume akaalEngine authorities).
# Nor may it depend on UI toolchains.
FORBIDDEN_IMPORTS = [
    "akaalPipeline",
    "akaalIPC",
    "akaalSoftware",
    "tauri",
    "react",
]


def _production_files():
    files = []
    for root, _, filenames in os.walk(os.path.join("akaalEngine", "intelligence")):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(root, filename))
    return files


def test_zero_fake_production_audit_intelligence_package():
    production_files = _production_files()
    assert len(production_files) >= 10, f"Expected at least 10 P7C.1 production files, found {len(production_files)}"

    violations = []
    for path in production_files:
        with open(path, "r", encoding="utf-8") as f:
            lower_content = f.read().lower()
            for pattern in FORBIDDEN_PRODUCTION_PATTERNS:
                if pattern in lower_content:
                    violations.append(f"{path}: contains forbidden marker {pattern!r}")

    assert not violations, "Zero-fake audit failed for akaalEngine/intelligence:\n" + "\n".join(violations)


def test_dependency_audit_no_forbidden_imports_intelligence_package():
    production_files = _production_files()

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

    assert not violations, "Dependency audit failed for akaalEngine/intelligence:\n" + "\n".join(violations)


def test_no_bare_except_swallowing_errors():
    """Every except clause in the package must name a specific exception type, or be
    the deliberate telemetry-must-never-fail-a-request guard in api.py (which logs
    and is explicitly commented as such) -- never a silent bare `except:`."""
    violations = []
    for path in _production_files():
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                violations.append(f"{path}:{node.lineno}: bare except clause")

    assert not violations, "Bare except audit failed:\n" + "\n".join(violations)
