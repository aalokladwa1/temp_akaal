"""
P7B.15 -- Locality & Data-Sovereignty Enforcement: positive, hostile, and the
directive's named India/EU/unknown scenarios.
"""

import pytest

from akaalEngine.fabric.locality.models import (
    LocalityConfidence,
    LocalityDimension,
    LocalityRecord,
    LocalitySubjectRole,
)
from akaalEngine.fabric.placement.residency import (
    ResidencyPolicy,
    ResidencyPolicyError,
    evaluate_residency,
)


def _rec(role, country=None, confidence=LocalityConfidence.PROVEN, stale=False, ref="ref-1", tenant="t1"):
    return LocalityRecord(
        subject_ref=ref, subject_role=role, tenant_id=tenant, country=country,
        confidence=confidence if country is not None else LocalityConfidence.UNKNOWN,
        provenance_source="PROVIDER_DISCOVERY", stale=stale,
    )


def _india_only_policy(roles):
    return ResidencyPolicy(policy_id="india-only", dimension=LocalityDimension.COUNTRY,
                            allowed_values=frozenset({"IN"}), required_roles=roles)


# ------------------------------------------------------------------ positive


def test_all_roles_compliant_passes():
    policy = _india_only_policy((LocalitySubjectRole.SOURCE, LocalitySubjectRole.TARGET))
    mapping = {
        LocalitySubjectRole.SOURCE: _rec(LocalitySubjectRole.SOURCE, "IN"),
        LocalitySubjectRole.TARGET: _rec(LocalitySubjectRole.TARGET, "IN"),
    }
    result = evaluate_residency(policy, mapping)
    assert result.compliant


# ------------------------------------------------------------------ hostile: unknown locality


def test_unknown_locality_never_satisfies_known_requirement():
    policy = _india_only_policy((LocalitySubjectRole.STAGING,))
    mapping = {LocalitySubjectRole.STAGING: _rec(LocalitySubjectRole.STAGING, country=None)}
    result = evaluate_residency(policy, mapping)
    assert not result.compliant
    assert "unknown locality cannot satisfy" in result.violations[0].reason


def test_missing_role_record_fails_closed():
    policy = _india_only_policy((LocalitySubjectRole.RELAY,))
    result = evaluate_residency(policy, {})
    assert not result.compliant
    assert "no locality record supplied" in result.violations[0].reason


def test_stale_record_fails_closed_even_if_previously_proven_india():
    policy = _india_only_policy((LocalitySubjectRole.SOURCE,))
    mapping = {LocalitySubjectRole.SOURCE: _rec(LocalitySubjectRole.SOURCE, "IN", stale=True)}
    result = evaluate_residency(policy, mapping)
    assert not result.compliant


def test_allow_unknown_explicit_opt_in_only_path_to_pass_unknown():
    policy = ResidencyPolicy(policy_id="lenient", dimension=LocalityDimension.COUNTRY,
                              allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.STAGING,),
                              allow_unknown=True)
    mapping = {LocalitySubjectRole.STAGING: _rec(LocalitySubjectRole.STAGING, country=None)}
    result = evaluate_residency(policy, mapping)
    assert result.compliant  # explicit opt-in only -- proves default (tested above) is the opposite


# ------------------------------------------------------------------ EU transit scenario (§25 of the directive)


def test_eu_endpoints_with_non_eu_transit_rejected():
    eu_only = ResidencyPolicy(policy_id="eu-only", dimension=LocalityDimension.COUNTRY,
                               allowed_values=frozenset({"DE", "FR", "NL", "IE", "IT", "ES"}),
                               required_roles=(LocalitySubjectRole.SOURCE, LocalitySubjectRole.RELAY, LocalitySubjectRole.TARGET))
    mapping = {
        LocalitySubjectRole.SOURCE: _rec(LocalitySubjectRole.SOURCE, "DE"),
        LocalitySubjectRole.RELAY: _rec(LocalitySubjectRole.RELAY, "US"),  # non-EU transit hop
        LocalitySubjectRole.TARGET: _rec(LocalitySubjectRole.TARGET, "FR"),
    }
    result = evaluate_residency(eu_only, mapping)
    assert not result.compliant
    assert any(v.role == LocalitySubjectRole.RELAY for v in result.violations)


def test_checking_only_endpoints_would_wrongly_pass_but_full_path_check_correctly_fails():
    """Demonstrates why P7B.15 must check the WHOLE path: a policy that only lists
    SOURCE/TARGET would pass this same non-compliant scenario -- proving under-scoping
    required_roles is the caller's choice, not this module's default."""
    endpoints_only = ResidencyPolicy(policy_id="eu-endpoints-only", dimension=LocalityDimension.COUNTRY,
                                      allowed_values=frozenset({"DE", "FR"}),
                                      required_roles=(LocalitySubjectRole.SOURCE, LocalitySubjectRole.TARGET))
    mapping = {
        LocalitySubjectRole.SOURCE: _rec(LocalitySubjectRole.SOURCE, "DE"),
        LocalitySubjectRole.RELAY: _rec(LocalitySubjectRole.RELAY, "US"),
        LocalitySubjectRole.TARGET: _rec(LocalitySubjectRole.TARGET, "FR"),
    }
    assert evaluate_residency(endpoints_only, mapping).compliant  # under-scoped policy: caller's mistake, demonstrated


# ------------------------------------------------------------------ malformed policy


def test_empty_allowed_values_rejected():
    with pytest.raises(ResidencyPolicyError):
        ResidencyPolicy(policy_id="p", dimension=LocalityDimension.COUNTRY, allowed_values=frozenset(), required_roles=(LocalitySubjectRole.SOURCE,))


def test_empty_required_roles_rejected():
    with pytest.raises(ResidencyPolicyError):
        ResidencyPolicy(policy_id="p", dimension=LocalityDimension.COUNTRY, allowed_values=frozenset({"IN"}), required_roles=())


def test_empty_policy_id_rejected():
    with pytest.raises(ResidencyPolicyError):
        ResidencyPolicy(policy_id="", dimension=LocalityDimension.COUNTRY, allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.SOURCE,))


# ------------------------------------------------------------------ hostile: cross-tenant locality substitution
# (found during Group-2 production-wiring hostile review -- evaluate_residency previously
# had NO tenant cross-check at all; a LocalityRecord genuinely proven for a DIFFERENT
# tenant would silently satisfy this tenant's policy merely by being placed under the
# right dict key. Fixed by expected_tenant_id.)


def test_cross_tenant_locality_record_rejected_when_expected_tenant_supplied():
    policy = _india_only_policy((LocalitySubjectRole.EXECUTION_SITE,))
    other_tenants_record = _rec(LocalitySubjectRole.EXECUTION_SITE, "IN", tenant="tenant-B-victim")
    mapping = {LocalitySubjectRole.EXECUTION_SITE: other_tenants_record}
    result = evaluate_residency(policy, mapping, expected_tenant_id="tenant-A-attacker-context")
    assert not result.compliant
    assert "cross-tenant" in result.violations[0].reason


def test_matching_tenant_record_still_satisfies_policy_when_expected_tenant_supplied():
    policy = _india_only_policy((LocalitySubjectRole.EXECUTION_SITE,))
    mapping = {LocalitySubjectRole.EXECUTION_SITE: _rec(LocalitySubjectRole.EXECUTION_SITE, "IN", tenant="tenant-A")}
    result = evaluate_residency(policy, mapping, expected_tenant_id="tenant-A")
    assert result.compliant


def test_no_expected_tenant_supplied_preserves_prior_behavior_for_backward_compatibility():
    """When a caller does not supply expected_tenant_id (pre-existing Campaign-C-only
    callers), behavior is unchanged -- the tenant check is opt-in, never a silent new
    requirement that would break existing callers."""
    policy = _india_only_policy((LocalitySubjectRole.EXECUTION_SITE,))
    mapping = {LocalitySubjectRole.EXECUTION_SITE: _rec(LocalitySubjectRole.EXECUTION_SITE, "IN", tenant="any-tenant")}
    result = evaluate_residency(policy, mapping)
    assert result.compliant
