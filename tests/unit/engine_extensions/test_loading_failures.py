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

    # IN_PROCESS is supported and returns cleanly
    assert IsolationManager.verify_isolation_mode(IsolationMode.IN_PROCESS, TrustTier.COMMUNITY) == IsolationMode.IN_PROCESS

    # SUBPROCESS_UNSUPPORTED, WASM_UNSUPPORTED, REMOTE_UNSUPPORTED fail closed
    for unsupported in (
        IsolationMode.SUBPROCESS_UNSUPPORTED,
        IsolationMode.WASM_UNSUPPORTED,
        IsolationMode.REMOTE_UNSUPPORTED,
    ):
        with pytest.raises(ExtensionRegistrationError) as exc_info:
            IsolationManager.verify_isolation_mode(unsupported, TrustTier.CORE_TRUSTED)
        assert f"Isolation mode '{unsupported.value}' is not physically implemented" in str(exc_info.value)
