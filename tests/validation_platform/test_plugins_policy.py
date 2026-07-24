"""Tests for Plugin system and Policy Engine."""

import pytest
from akaal.validation.plugins.registry import PluginRegistry
from akaal.validation.plugins.metadata import PluginMetadata, PluginVersion
from akaal.validation.policy.engine import PolicyEngine
from akaal.validation.core.config import PolicyProfile
from akaal.validation.core.models import ValidationResult, ValidationStatus, ValidationIssue, SeverityLevel


def test_policy_engine_finance():
    engine = PolicyEngine(profile=PolicyProfile.FINANCE)
    res_pass = ValidationResult(
        domain_name="D1",
        capabilities_tested=["Cap 1"],
        status=ValidationStatus.PASSED,
        confidence_score=100.0,
        failed_count=0,
    )
    eval_pass = engine.evaluate(res_pass)
    assert eval_pass["compliant"] is True

    res_fail = ValidationResult(
        domain_name="D1",
        capabilities_tested=["Cap 1"],
        status=ValidationStatus.FAILED,
        confidence_score=90.0,
        failed_count=1,
    )
    eval_fail = engine.evaluate(res_fail)
    assert eval_fail["compliant"] is False
    assert len(eval_fail["violations"]) > 0


def test_plugin_registry():
    registry = PluginRegistry()
    meta = PluginMetadata(plugin_name="custom_plugin", version=PluginVersion(1, 0, 0))

    class MockPlugin:
        @property
        def plugin_name(self):
            return "custom_plugin"

        @property
        def version(self):
            return "1.0.0"

        def initialize(self, ctx):
            pass

        def get_validators(self):
            return []

    p = MockPlugin()
    registry.register_plugin(p, meta)
    assert registry.get_plugin("custom_plugin") == p
    assert "custom_plugin" in registry.list_plugins()
