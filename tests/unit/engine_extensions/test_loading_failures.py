"""
tests.unit.engine_extensions.test_loading_failures
==================================================
Tests for explicit module/entry point loading and failure containment.
"""

import pytest
from akaalEngine.extensions.loading.loader import ExtensionLoader
from akaalEngine.extensions.errors.taxonomy import ExtensionLoadingError


def test_loading_from_nonexistent_module_fails_cleanly():
    with pytest.raises(ExtensionLoadingError) as exc_info:
        ExtensionLoader.load_from_module("nonexistent_extension_module_xyz")
    assert "Failed to import extension module" in str(exc_info.value)


def test_loading_from_invalid_module_structure():
    # Attempting to load from a module that lacks get_manifest() or EXTENSION_MANIFEST
    with pytest.raises(ExtensionLoadingError) as exc_info:
        ExtensionLoader.load_from_module("os")
    assert "does not define 'get_manifest()'" in str(exc_info.value)


def test_unsupported_isolation_modes_rejected():
    from akaalEngine.extensions.loading.isolation import IsolationManager
    from akaalEngine.extensions.models.enums import IsolationMode, TrustTier
    from akaalEngine.extensions.errors.taxonomy import ExtensionRegistrationError

    # IN_PROCESS and SUBPROCESS are physically implemented (see P7A.3 akaalEngine.extensions.sandbox)
    # and return cleanly.
    assert IsolationManager.verify_isolation_mode(IsolationMode.IN_PROCESS, TrustTier.COMMUNITY) == IsolationMode.IN_PROCESS
    assert IsolationManager.verify_isolation_mode(IsolationMode.SUBPROCESS, TrustTier.COMMUNITY) == IsolationMode.SUBPROCESS

    # WASM_UNSUPPORTED, REMOTE_UNSUPPORTED still fail closed -- no WASM runtime or remote
    # worker infrastructure exists in this repository/environment.
    for unsupported in (
        IsolationMode.WASM_UNSUPPORTED,
        IsolationMode.REMOTE_UNSUPPORTED,
    ):
        with pytest.raises(ExtensionRegistrationError) as exc_info:
            IsolationManager.verify_isolation_mode(unsupported, TrustTier.CORE_TRUSTED)
        assert f"Isolation mode '{unsupported.value}' is not physically implemented" in str(exc_info.value)
