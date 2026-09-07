"""
tests.unit.engine_fabric.test_p7b33_explainability
=======================================================
P7B.33 -- Topology & Placement Explainability hostile test suite.

Proves explain_placement/explain_failover (pure formatters over the UNMODIFIED Group-2
evaluate_candidates / P7B.28 attempt_failover results) are:
    * deterministic (same artifact -> byte-identical explanation, always)
    * exactly traceable to the real decision artifact (no fabricated content)
    * immune to cross-tenant contamination (no shared mutable state)
    * inert with respect to mutated/tampered decision artifacts (frozen dataclasses)
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.explainability import explain_failover, explain_placement
from akaalEngine.fabric.failover.models import FailoverOutcome, FailoverResult
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.engine import evaluate_candidates


def _trusted_site(registry, site_id, tenant_id="tenant-a"):
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", claimed_security_identity=f"spiffe://x/{site_id}"))
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry.get(site_id)


def _placement_result(tenant_id, site_ids, capable_site_ids):
    registry = SiteRegistry()
    sites = [_trusted_site(registry, sid, tenant_id) for sid in site_ids]
    cap = frozenset({"postgresql"})
    capable_sites = []
    for site in sites:
        if site.site_id in capable_site_ids:
            site = ExecutionSite(**{**site.__dict__, "capabilities": cap})
        capable_sites.append(site)
    requirement = CapabilityRequirement(required_capabilities=cap, plan_reference=f"plan-{tenant_id}")
    return evaluate_candidates(
        plan_reference=f"plan-{tenant_id}", candidates=capable_sites, capability_requirement=requirement,
        actor_context={}, authorization_action="execute", authorization_callback=lambda *a: True,
        tenant_id=tenant_id,
    )


def test_explanation_is_deterministic():
    result = _placement_result("tenant-a", ["site-1", "site-2"], ["site-1"])
    e1 = explain_placement(result)
    e2 = explain_placement(result)
    assert e1 == e2


def test_explanation_traces_exactly_to_real_decision():
    result = _placement_result("tenant-a", ["site-1", "site-2"], ["site-1"])
    explanation = explain_placement(result)
    accepted_ids = {a["site_id"] for a in explanation["accepted"]}
    rejected_ids = {r["site_id"] for r in explanation["rejected"]}
    assert accepted_ids == {"site-1"}
    assert rejected_ids == {"site-2"}
    assert explanation["compliant"] is True


def test_rejection_explanation_carries_real_stage_not_fabricated():
    result = _placement_result("tenant-a", ["site-2"], [])  # site-2 lacks capability
    explanation = explain_placement(result)
    assert explanation["rejected"][0]["stage"] == "CAPABILITY"
    assert explanation["compliant"] is False


def test_two_tenants_explanations_never_cross_contaminate():
    result_a = _placement_result("tenant-a", ["site-a1"], ["site-a1"])
    result_b = _placement_result("tenant-b", ["site-b1"], [])  # rejected

    explanation_a = explain_placement(result_a)
    explanation_b = explain_placement(result_b)

    a_ids = {x["site_id"] for x in explanation_a["accepted"]} | {x["site_id"] for x in explanation_a["rejected"]}
    b_ids = {x["site_id"] for x in explanation_b["accepted"]} | {x["site_id"] for x in explanation_b["rejected"]}
    assert a_ids == {"site-a1"}
    assert b_ids == {"site-b1"}
    assert a_ids.isdisjoint(b_ids)
    # Building tenant B's explanation must not have altered tenant A's already-built one.
    assert explain_placement(result_a) == explanation_a


def test_decision_artifact_is_immutable_cannot_be_tampered_post_hoc():
    result = _placement_result("tenant-a", ["site-1"], ["site-1"])
    with pytest.raises(Exception):
        result.accepted = ()  # frozen dataclass -- must reject mutation attempts
    with pytest.raises(Exception):
        result.accepted[0].site_id = "forged-site"  # frozen dataclass -- element-level tamper


def test_failover_explanation_omits_placement_detail_when_not_reached():
    fake_result = FailoverResult(
        outcome=FailoverOutcome.NOT_REQUIRED, old_ownership_key="k",
        old_record=None, new_record=None, selected_site_id=None, placement_result=None,
        reasons=("site still healthy",),
    )
    explanation = explain_failover(fake_result)
    assert explanation["placement_explanation"] is None
    assert explanation["outcome"] == "NOT_REQUIRED"


def test_failover_explanation_includes_placement_detail_when_evaluated():
    placement = _placement_result("tenant-a", ["site-1"], ["site-1"])
    fake_result = FailoverResult(
        outcome=FailoverOutcome.SUCCEEDED, old_ownership_key="k",
        old_record=None, new_record=None, selected_site_id="site-1", placement_result=placement,
        reasons=("failed over",),
    )
    explanation = explain_failover(fake_result)
    assert explanation["placement_explanation"] is not None
    assert explanation["placement_explanation"]["compliant"] is True
