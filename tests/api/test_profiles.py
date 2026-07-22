"""
Unit tests for Configuration Profiles.
"""

import os
import pytest
from akaal.api.profiles.manager import ProfileManager


def test_profile_loading():
    mgr = ProfileManager(default_profile_name="Production")
    assert mgr.active_profile.profile_name == "Production"
    assert mgr.active_profile.enable_mtls is True

    dev_mgr = ProfileManager(default_profile_name="Development")
    assert dev_mgr.active_profile.profile_name == "Development"
    assert dev_mgr.active_profile.enable_cors is True


def test_env_var_resolution():
    os.environ["TEST_DB_HOST"] = "prod-db.internal"
    mgr = ProfileManager()
    resolved = mgr.resolve_environment_variables("postgresql://${TEST_DB_HOST}:5432/db")
    assert resolved == "postgresql://prod-db.internal:5432/db"


def test_secret_reference_resolution():
    os.environ["MY_SECRET_KEY"] = "super-secret-pass"
    mgr = ProfileManager()
    resolved_env = mgr.resolve_secret_reference("env:MY_SECRET_KEY")
    assert resolved_env == "super-secret-pass"

    resolved_vault = mgr.resolve_secret_reference("vault:secret/data/db")
    assert "RESOLVED_VAULT_SECRET" in resolved_vault
