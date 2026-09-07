"""
tests.unit.engine_fabric.test_p7b32_fabric_observability
=============================================================
P7B.32 -- Fabric Observability hostile test suite.

Proves akaalEngine.fabric.telemetry_integration:
    * carries no secret/credential-shaped parameters anywhere (structural signature scan)
    * is never imported by any P7B.24-31 decision module (telemetry != execution truth --
      a decision must remain correct even if telemetry is never wired up at all)
    * event/label builders faithfully reflect their inputs (no silent transformation that
      could misrepresent what actually happened)
"""

from __future__ import annotations

import inspect

import akaalEngine.fabric.telemetry_integration as telemetry_integration

_BANNED_PARAM_SUBSTRINGS = ("password", "secret", "token", "private_key", "credential", "api_key")

_DECISION_MODULES = [
    "akaalEngine.fabric.site_coordination.coordinator",
    "akaalEngine.fabric.ownership.manager",
    "akaalEngine.fabric.regional_operation.evaluator",
    "akaalEngine.fabric.multi_cloud.evaluator",
    "akaalEngine.fabric.failover.coordinator",
    "akaalEngine.fabric.gitops.reconciler",
]


def test_no_secret_shaped_parameters_anywhere_in_module():
    for name, fn in inspect.getmembers(telemetry_integration, inspect.isfunction):
        for param_name in inspect.signature(fn).parameters:
            lowered = param_name.lower()
            for banned in _BANNED_PARAM_SUBSTRINGS:
                assert banned not in lowered, f"{name}({param_name}) looks secret-shaped"


def test_no_decision_module_imports_telemetry_integration():
    for module_name in _DECISION_MODULES:
        module = __import__(module_name, fromlist=["_"])
        source = inspect.getsource(module)
        assert "telemetry_integration" not in source, f"{module_name} must not depend on telemetry for its decisions"


def test_ownership_event_faithfully_reflects_inputs():
    event = telemetry_integration.ownership_event(
        event_type="fabric.ownership.acquired", ownership_key="tenant-a::mig-1::plan-1",
        tenant_id="tenant-a", site_id="site-1", worker_id="worker-1",
        fencing_generation=3, correlation_id="corr-1", outcome="SUCCEEDED",
    )
    assert event["fencing_generation"] == 3
    assert event["ownership_key"] == "tenant-a::mig-1::plan-1"
    assert event["event_type"] == "fabric.ownership.acquired"


def test_failover_event_reports_none_new_site_when_no_compliant_candidate():
    event = telemetry_integration.failover_event(
        outcome="NO_COMPLIANT_CANDIDATE", old_ownership_key="k", old_site_id="site-mumbai",
        new_site_id=None, reasons=("zero candidates survived",),
    )
    assert event["new_site_id"] is None
    assert event["outcome"] == "NO_COMPLIANT_CANDIDATE"


def test_region_health_labels_are_plain_strings_not_objects():
    labels = telemetry_integration.region_health_labels("ap-south-1", "UNAVAILABLE")
    assert all(isinstance(v, str) for v in labels.values())
