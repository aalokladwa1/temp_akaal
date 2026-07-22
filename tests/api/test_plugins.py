"""
Unit tests for Sandboxed Plugin Manager.
"""

import pytest
from akaal.api.contracts.errors import PluginError
from akaal.api.plugins.manager import PluginManifest, PluginManager


def test_plugin_lifecycle():
    mgr = PluginManager()
    manifest = PluginManifest(
        name="custom_auth_plugin",
        version="1.0.0",
        capabilities=["authenticate_custom"],
        is_signed=True,
    )

    mgr.install_plugin(manifest)
    mgr.activate_plugin("custom_auth_plugin")

    res = mgr.execute_capability("custom_auth_plugin", "authenticate_custom")
    assert res["status"] == "SUCCESS"

    # Execution of undeclared capability fails
    with pytest.raises(PluginError):
        mgr.execute_capability("custom_auth_plugin", "undeclared_cap")


def test_unsigned_plugin_rejection():
    mgr = PluginManager()
    manifest = PluginManifest(
        name="malicious_plugin", version="1.0.0", is_signed=False
    )
    with pytest.raises(PluginError):
        mgr.install_plugin(manifest)
