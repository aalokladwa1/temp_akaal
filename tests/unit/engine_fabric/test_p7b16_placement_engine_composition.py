"""
P7B.13-15 composition (akaalEngine.fabric.placement.engine): the directive's named
hostile acceptance scenario -- India source/target, four candidates (compliant,
cheaper-but-non-compliant, incapable, unauthorized) -- and the "only Singapore remains"
NO COMPLIANT PLACEMENT scenario.
"""

from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind, SiteTrustState
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.engine import evaluate_candidates
from akaalEngine.fabric.placement.residency import ResidencyPolicy


def _site(site_id, caps, trust=SiteTrustState.TRUSTED):
    return ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id=f"env-{site_id}",
                          capabilities=frozenset(caps), trust_state=trust)


def _locality(site_id, country):
    return {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
        subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id="t1",
        country=country, confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )}


INDIA_ONLY = ResidencyPolicy(policy_id="india-only", dimension=LocalityDimension.COUNTRY,
                              allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.EXECUTION_SITE,))

REQ = CapabilityRequirement(required_capabilities=frozenset({"oracle", "postgresql"}), plan_reference="oracle-to-pg-india")


def _authz(allowed_site_ids):
    def cb(site, actor, action, ctx):
        return site.site_id in allowed_site_ids
    return cb


def test_india_scenario_a_wins_b_c_d_rejected_for_distinct_reasons():
    site_a = _site("A-mumbai", {"oracle", "postgresql"})       # compliant, capable, authorized
    site_b = _site("B-singapore", {"oracle", "postgresql"})    # capable, cheaper, WRONG country
    site_c = _site("C-mumbai-incapable", {"postgresql"})       # right country, missing oracle capability
    site_d = _site("D-mumbai-unauthorized", {"oracle", "postgresql"})  # capable, right country, NOT authorized

    result = evaluate_candidates(
        plan_reference="oracle-to-pg-india",
        candidates=[site_a, site_b, site_c, site_d],
        capability_requirement=REQ,
        actor_context={"tenant": "t1"}, authorization_action="assign_execution",
        authorization_callback=_authz({"A-mumbai", "B-singapore", "C-mumbai-incapable"}),  # D deliberately excluded
        residency_policies=(INDIA_ONLY,),
        locality_by_site={
            "A-mumbai": _locality("A-mumbai", "IN"),
            "B-singapore": _locality("B-singapore", "SG"),
            "C-mumbai-incapable": _locality("C-mumbai-incapable", "IN"),
            "D-mumbai-unauthorized": _locality("D-mumbai-unauthorized", "IN"),
        },
    )

    accepted_ids = {a.site_id for a in result.accepted}
    assert accepted_ids == {"A-mumbai"}
    assert result.has_compliant_placement()

    rejections = {r.site_id: r.stage for r in result.rejected}
    assert rejections["B-singapore"] == "RESIDENCY"
    assert rejections["C-mumbai-incapable"] == "CAPABILITY"
    assert rejections["D-mumbai-unauthorized"] == "AUTHORIZATION"


def test_capable_authorized_but_wrong_country_rejected_at_residency_not_resurrected_by_cost():
    site_b = _site("B-singapore", {"oracle", "postgresql"})
    result = evaluate_candidates(
        plan_reference="oracle-to-pg-india",
        candidates=[site_b],
        capability_requirement=REQ,
        actor_context={}, authorization_action="assign_execution",
        authorization_callback=lambda *a: True,  # fully authorized
        residency_policies=(INDIA_ONLY,),
        locality_by_site={"B-singapore": _locality("B-singapore", "SG")},
    )
    assert not result.accepted
    assert result.rejected[0].stage == "RESIDENCY"


def test_only_remaining_candidate_noncompliant_yields_no_compliant_placement():
    """India-only migration; the only technically-reachable/capable/authorized remaining
    candidate is Singapore -- must yield NO COMPLIANT PLACEMENT, never a silent fallback."""
    site_b = _site("B-singapore", {"oracle", "postgresql"})
    result = evaluate_candidates(
        plan_reference="oracle-to-pg-india",
        candidates=[site_b],
        capability_requirement=REQ,
        actor_context={}, authorization_action="assign_execution",
        authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,),
        locality_by_site={"B-singapore": _locality("B-singapore", "SG")},
    )
    assert result.has_compliant_placement() is False
    assert result.accepted == ()


def test_unsupported_capability_stops_before_authorization_or_residency_ever_runs():
    """Proves zero authorization/residency evaluation happens for an incapable site --
    the negative-capability law: rejection must happen at the earliest possible stage."""
    calls = {"authz": 0}

    def cb(site, actor, action, ctx):
        calls["authz"] += 1
        return True

    incapable = _site("incapable", {"postgresql"})
    result = evaluate_candidates(
        plan_reference="oracle-to-pg-india", candidates=[incapable], capability_requirement=REQ,
        actor_context={}, authorization_action="assign_execution", authorization_callback=cb,
        residency_policies=(INDIA_ONLY,), locality_by_site={},
    )
    assert not result.accepted
    assert result.rejected[0].stage == "CAPABILITY"
    assert calls["authz"] == 0  # authorization callback never invoked for an incapable site
