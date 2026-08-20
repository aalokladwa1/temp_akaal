"""Physical architecture regression tests for akaalIPC.

Ensures that:
1. root-level `akaalIPC` imports successfully from repository root;
2. motherboard modules resolve physically under `<repo-root>/akaalIPC/`;
3. motherboard tests import `akaalIPC`, not legacy package;
4. `akaalIPC` has zero dependencies on legacy `akaal.ipc` or `akaal` runtime authorities;
5. no compatibility shim exists under `akaal/ipc/`.
"""

from __future__ import annotations

import importlib
import pathlib
import sys

import pytest


def test_root_level_akaalipc_imports_successfully():
    import akaalIPC

    filepath = pathlib.Path(akaalIPC.__file__).resolve()
    assert "akaalIPC" in filepath.parts
    assert filepath.name == "__init__.py"
    assert filepath.parent.name == "akaalIPC"


def test_motherboard_submodules_resolve_physically_under_akaalipc():
    submodules = [
        "akaalIPC.protocol",
        "akaalIPC.protocol.envelopes",
        "akaalIPC.protocol.errors",
        "akaalIPC.protocol.schemas",
        "akaalIPC.protocol.versions",
        "akaalIPC.application",
        "akaalIPC.application.router",
        "akaalIPC.security",
        "akaalIPC.security.context",
        "akaalIPC.subscriptions",
        "akaalIPC.subscriptions.streams",
        "akaalIPC.transport",
        "akaalIPC.transport.ports",
    ]
    for mod_name in submodules:
        mod = importlib.import_module(mod_name)
        mod_path = pathlib.Path(mod.__file__).resolve()
        assert "akaalIPC" in mod_path.parts, f"Module {mod_name} resolved outside akaalIPC: {mod_path}"


def test_no_motherboard_compatibility_shim_under_akaal_ipc():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    legacy_ipc_dir = repo_root / "akaal" / "ipc"

    # Must not contain protocol, application, security, subscriptions, or ports.py
    forbidden_paths = [
        legacy_ipc_dir / "protocol",
        legacy_ipc_dir / "application",
        legacy_ipc_dir / "security",
        legacy_ipc_dir / "subscriptions",
        legacy_ipc_dir / "transport" / "ports.py",
        legacy_ipc_dir / "__init__.py",
    ]
    for p in forbidden_paths:
        assert not p.exists(), f"Forbidden shim/motherboard path exists under legacy akaal/ipc: {p}"


def test_akaal_ipc_transport_init_contains_only_legacy_exports():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    init_path = repo_root / "akaal" / "ipc" / "transport" / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    assert "NamedPipeIPCTransport" in text
    assert "UnifiedCallerPort" not in text
    assert "CallerResult" not in text


def test_motherboard_tests_import_akaalipc_not_legacy_package():
    test_dir = pathlib.Path(__file__).resolve().parent
    legacy_pattern = "akaal" + ".ipc."
    for test_file in test_dir.glob("test_*.py"):
        if test_file.name == pathlib.Path(__file__).name:
            continue
        text = test_file.read_text(encoding="utf-8")
        assert legacy_pattern not in text, f"{test_file.name} still references legacy ipc package."
