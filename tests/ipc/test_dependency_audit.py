"""Static audits over the root-level akaalIPC production source tree.

These tests are the automated half of the zero-fake / dependency-boundary
audit required before akaalIPC can be declared complete. They inspect the
actual files under root-level ``akaalIPC/`` (with ZERO exclusions) rather
than relying on developer memory to keep the package honest over time.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

IPC_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[2] / "akaalIPC"

FORBIDDEN_IMPORT_PREFIXES = (
    "akaal",
    "akaal.engine",
    "akaal.gateway",
    "akaal.connectors",
    "akaal.cdc",
    "akaal.validation",
    "akaal.migration",
    "akaal.workflow",
    "akaal.orchestration",
    "akaal.replication",
    "akaal.distributed",
    "akaal.streaming",
)

EXCLUDED_FILES: set[str] = set()


def _new_ipc_python_files():
    return sorted(
        p for p in IPC_PACKAGE_ROOT.rglob("*.py") if p.name not in EXCLUDED_FILES and "__pycache__" not in p.parts
    )


@pytest.mark.parametrize("path", _new_ipc_python_files(), ids=lambda p: str(p.relative_to(IPC_PACKAGE_ROOT)))
def test_no_forbidden_downstream_imports(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    for module in imported:
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            if forbidden == "akaal" and module.startswith("akaalIPC"):
                continue
            assert not module.startswith(forbidden), f"{path}: forbidden import of {module}"


@pytest.mark.parametrize("path", _new_ipc_python_files(), ids=lambda p: str(p.relative_to(IPC_PACKAGE_ROOT)))
def test_no_ui_or_tauri_imports(path: pathlib.Path):
    """akaalIPC's docs may name Tauri/CLI/REST/Assistant as future callers
    (that's the whole point of the port-based design) — what's forbidden is
    actually importing/executing against the current UI's source tree or a
    Tauri/React runtime package, not mentioning them in prose."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    for module in imported:
        for marker in ("tauri", "react", "akaal_software"):
            assert marker not in module.lower(), f"{path}: imports {module!r} — akaalIPC must not couple to the UI"


@pytest.mark.parametrize("path", _new_ipc_python_files(), ids=lambda p: str(p.relative_to(IPC_PACKAGE_ROOT)))
def test_no_dynamic_import_or_eval_or_exec(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__"}, f"{path}: uses {node.func.id}()"
        if isinstance(node, ast.Attribute) and node.attr == "loads" and isinstance(node.value, ast.Name):
            # pickle.loads / marshal.loads would allow arbitrary object
            # construction from untrusted payloads.
            assert node.value.id not in {"pickle", "marshal"}, f"{path}: uses {node.value.id}.loads"


@pytest.mark.parametrize("path", _new_ipc_python_files(), ids=lambda p: str(p.relative_to(IPC_PACKAGE_ROOT)))
def test_no_suspicious_fake_markers_in_production_code(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    suspicious_markers = ("todo", "fixme", "notimplementederror", "mock", "dummy", "fake ", "placeholder", "hardcoded")
    hits = [m for m in suspicious_markers if m in lowered]
    # None of these markers appear anywhere in the newly authored akaalIPC
    # production files. If this test ever fails, the occurrence must be
    # inspected and classified (removed / legitimate / test-only) per the
    # zero-fake audit, not silently allowed.
    assert hits == [], f"{path}: contains suspicious marker(s) {hits}"


def test_no_bare_except_swallowing_errors_into_success():
    for path in _new_ipc_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail(f"{path}:{node.lineno}: bare 'except:' clause found")
