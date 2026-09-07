"""
P7B.12 -- Data Locality Model: positive, hostile, and cross-tenant tests.
"""

import pytest

from akaalEngine.fabric.locality.models import (
    LocalityConfidence,
    LocalityDimension,
    LocalityRecord,
    LocalitySubjectRole,
    LocalityValidationError,
)
from akaalEngine.fabric.locality.registry import (
    CrossTenantLocalityError,
    LocalityRegistry,
    UnknownLocalityError,
)


def _proven_india(subject_ref="src-1", role=LocalitySubjectRole.SOURCE, tenant="t1"):
    return LocalityRecord(
        subject_ref=subject_ref, subject_role=role, tenant_id=tenant,
        country="IN", region="ap-south-1", cloud_provider="AWS",
        confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )


# ------------------------------------------------------------------ positive


def test_proven_value_readable_for_proven_dimension():
    rec = _proven_india()
    assert rec.proven_value_for(LocalityDimension.COUNTRY) == "IN"
    assert rec.is_proven(LocalityDimension.COUNTRY)


def test_satisfies_true_and_false_for_proven_dimension():
    rec = _proven_india()
    assert rec.satisfies(LocalityDimension.COUNTRY, {"IN"}) is True
    assert rec.satisfies(LocalityDimension.COUNTRY, {"SG", "US"}) is False


def test_registry_register_and_get_current_roundtrip():
    reg = LocalityRegistry()
    reg.register(_proven_india())
    got = reg.get_current("src-1", LocalitySubjectRole.SOURCE, "t1")
    assert got.country == "IN"


def test_registry_history_preserves_prior_observations():
    reg = LocalityRegistry()
    reg.register(_proven_india())
    reg.register(_proven_india())  # re-observation
    hist = reg.history("src-1", LocalitySubjectRole.SOURCE, "t1")
    assert len(hist) == 2


def test_mark_stale_preserves_values_but_flips_flag():
    reg = LocalityRegistry()
    reg.register(_proven_india())
    updated = reg.mark_stale("src-1", LocalitySubjectRole.SOURCE, "t1")
    assert updated.stale is True
    assert updated.country == "IN"  # value preserved, just no longer trusted as current


# ------------------------------------------------------------------ hostile: unknown must remain unknown


def test_unset_dimension_is_none_never_inferred():
    rec = LocalityRecord(
        subject_ref="s1", subject_role=LocalitySubjectRole.STAGING, tenant_id="t1",
        cloud_provider="AWS", region="ap-south-1",
        confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )
    # region/cloud_provider proven, but country/jurisdiction were never supplied --
    # must stay None, never derived from region or cloud_provider.
    assert rec.proven_value_for(LocalityDimension.COUNTRY) is None
    assert rec.proven_value_for(LocalityDimension.JURISDICTION) is None
    assert rec.satisfies(LocalityDimension.COUNTRY, {"IN"}) is None  # not False -- unknown


def test_claimed_confidence_never_satisfies_a_proof_requirement():
    rec = LocalityRecord(
        subject_ref="s1", subject_role=LocalitySubjectRole.STAGING, tenant_id="t1",
        country="IN", confidence=LocalityConfidence.CLAIMED, provenance_source="OPERATOR_CONFIGURATION",
    )
    # value_for (unchecked) sees the claim, but proven_value_for refuses it.
    assert rec.value_for(LocalityDimension.COUNTRY) == "IN"
    assert rec.proven_value_for(LocalityDimension.COUNTRY) is None
    assert rec.satisfies(LocalityDimension.COUNTRY, {"IN"}) is None


def test_unknown_confidence_never_satisfies_anything():
    rec = LocalityRecord(
        subject_ref="s1", subject_role=LocalitySubjectRole.RELAY, tenant_id="t1",
        country="IN",  # value present but confidence still UNKNOWN
    )
    assert rec.satisfies(LocalityDimension.COUNTRY, {"IN"}) is None


def test_stale_record_never_satisfies_even_if_proven():
    reg = LocalityRegistry()
    reg.register(_proven_india())
    stale = reg.mark_stale("src-1", LocalitySubjectRole.SOURCE, "t1")
    assert stale.satisfies(LocalityDimension.COUNTRY, {"IN"}) is None


def test_proven_confidence_with_no_dimension_set_is_rejected_as_caller_bug():
    with pytest.raises(LocalityValidationError):
        LocalityRecord(
            subject_ref="s1", subject_role=LocalitySubjectRole.SOURCE, tenant_id="t1",
            confidence=LocalityConfidence.PROVEN,  # claims proof of nothing
            provenance_source="PROVIDER_DISCOVERY",
        )


def test_empty_provenance_source_rejected():
    with pytest.raises(LocalityValidationError):
        LocalityRecord(
            subject_ref="s1", subject_role=LocalitySubjectRole.SOURCE, tenant_id="t1",
            provenance_source="",
        )


# ------------------------------------------------------------------ hostile: cross-tenant


def test_cross_tenant_get_current_raises_unknown_not_leaks():
    reg = LocalityRegistry()
    reg.register(_proven_india(tenant="t1"))
    with pytest.raises(UnknownLocalityError):
        reg.get_current("src-1", LocalitySubjectRole.SOURCE, "t2-attacker")


def test_cross_tenant_mark_stale_raises_unknown():
    reg = LocalityRegistry()
    reg.register(_proven_india(tenant="t1"))
    with pytest.raises(UnknownLocalityError):
        reg.mark_stale("src-1", LocalitySubjectRole.SOURCE, "t2-attacker")


def test_list_current_for_tenant_never_leaks_other_tenants():
    reg = LocalityRegistry()
    reg.register(_proven_india(subject_ref="src-1", tenant="t1"))
    reg.register(_proven_india(subject_ref="src-2", tenant="t2"))
    t1_records = reg.list_current_for_tenant("t1")
    assert len(t1_records) == 1
    assert t1_records[0].subject_ref == "src-1"


def test_same_subject_ref_different_tenants_do_not_collide():
    reg = LocalityRegistry()
    reg.register(_proven_india(subject_ref="shared-ref", tenant="t1"))
    other = LocalityRecord(
        subject_ref="shared-ref", subject_role=LocalitySubjectRole.SOURCE, tenant_id="t2",
        country="SG", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )
    reg.register(other)
    assert reg.get_current("shared-ref", LocalitySubjectRole.SOURCE, "t1").country == "IN"
    assert reg.get_current("shared-ref", LocalitySubjectRole.SOURCE, "t2").country == "SG"


# ------------------------------------------------------------------ hostile: unknown lookups fail safely


def test_unknown_subject_raises_not_fabricated_default():
    reg = LocalityRegistry()
    with pytest.raises(UnknownLocalityError):
        reg.get_current("no-such-subject", LocalitySubjectRole.SOURCE, "t1")


def test_try_get_current_returns_none_for_unknown():
    reg = LocalityRegistry()
    assert reg.try_get_current("no-such-subject", LocalitySubjectRole.SOURCE, "t1") is None


# ------------------------------------------------------------------ EU/relay/staging path scenario (P7B.15 precursor)


def test_role_scoped_records_distinguish_source_from_staging_for_same_migration():
    reg = LocalityRegistry()
    reg.register(LocalityRecord(
        subject_ref="oracle-mumbai", subject_role=LocalitySubjectRole.SOURCE, tenant_id="t1",
        country="IN", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    ))
    reg.register(LocalityRecord(
        subject_ref="staging-singapore", subject_role=LocalitySubjectRole.STAGING, tenant_id="t1",
        country="SG", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    ))
    source = reg.get_current("oracle-mumbai", LocalitySubjectRole.SOURCE, "t1")
    staging = reg.get_current("staging-singapore", LocalitySubjectRole.STAGING, "t1")
    assert source.satisfies(LocalityDimension.COUNTRY, {"IN"}) is True
    # A residency policy requiring India-only would need to check EVERY role in the path,
    # not just source/target -- staging here truthfully fails that check.
    assert staging.satisfies(LocalityDimension.COUNTRY, {"IN"}) is False
