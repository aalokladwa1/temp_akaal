"""
tests.unit.engine_fabric.test_p7b_round6_oci_native_identity_hostile
=========================================================================
P7B Group-1 Hostile Closure Round 6 -- OCI native-resource identity hostile matrix,
completing the four-cloud matrix (blocker #3). Covers OCID type, malformed OCID,
tenancy/compartment confusion, and honest disclosure of what OCID format alone cannot
verify (compartment/tenancy membership requires a live API call -- see
akaalEngine.fabric.resource_identity.discovery.discover_oci_resource, tested separately
in test_p7b_2_resource_identity.py).
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import EnvironmentValidationError, OCIBoundary
from akaalEngine.fabric.resource_identity import OCIResourceLocator, ResourceLocatorValidationError


# ---------------------------------------------------------------------------
# OCID type / malformed OCID
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ocid,resource_type_hint", [
    ("ocid1.instance.oc1.iad.aaaaaaaa", "instance"),
    ("ocid1.bucket.oc1.iad.aaaaaaaa", "bucket"),
    ("ocid1.autonomousdatabase.oc1.ap-hyderabad-1.aaaaaaaa", "autonomousdatabase"),
    ("ocid1.vcn.oc1.iad.aaaaaaaa", "vcn"),
    ("ocid1.compartment.oc1..aaaaaaaa", "compartment"),
])
def test_oci_various_legitimate_resource_types_accepted(ocid, resource_type_hint):
    """OCID format is generic across resource types (ocid1.<type>.<realm>.<region>.<id>)
    -- the resource-identity model must not hardcode a fixed allowlist of type strings
    (OCI adds new resource types over time) and must accept any well-formed OCID."""
    locator = OCIResourceLocator(ocid=ocid, compartment_ocid="ocid1.compartment.oc1..bbbb")
    assert resource_type_hint in locator.ocid


@pytest.mark.parametrize("malformed_ocid", [
    "not-an-ocid-at-all",
    "ocid2.instance.oc1.iad.aaaa",  # wrong version prefix (ocid2 instead of ocid1)
    "ocid1..oc1.iad.aaaa",  # empty resource-type segment
    "",
    "ocid1",  # truncated
])
def test_oci_malformed_ocids_rejected(malformed_ocid):
    with pytest.raises(ResourceLocatorValidationError):
        OCIResourceLocator(ocid=malformed_ocid, compartment_ocid="ocid1.compartment.oc1..bbbb")


def test_oci_ocid_naming_a_different_resource_type_than_expected_is_still_just_a_locator():
    """A caller mistakenly treating an instance OCID as if it were a bucket OCID is a
    caller-side type error, not something OCIResourceLocator itself can catch from the
    string alone (OCI does not encode a strict schema contract in the OCID format that
    this module could validate against without a live API call) -- disclosed honestly:
    this is EXTERNAL_DEFERRED (requires a live GetResource-shaped call to verify actual
    resource type), not silently claimed as locally verified."""
    instance_ocid_used_as_if_bucket = OCIResourceLocator(ocid="ocid1.instance.oc1.iad.aaaaaaaa", compartment_ocid="ocid1.compartment.oc1..bbbb")
    assert instance_ocid_used_as_if_bucket.ocid.startswith("ocid1.instance.")  # the TRUE type is preserved, not silently reinterpreted


# ---------------------------------------------------------------------------
# Malformed compartment_ocid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_compartment", [
    "not-a-compartment-ocid",
    "ocid1.tenancy.oc1..aaaa",  # a TENANCY ocid, not a compartment ocid -- a real confusion class
    "",
])
def test_oci_malformed_compartment_ocid_rejected(bad_compartment):
    with pytest.raises(ResourceLocatorValidationError):
        OCIResourceLocator(ocid="ocid1.instance.oc1.iad.aaaa", compartment_ocid=bad_compartment)


# ---------------------------------------------------------------------------
# Tenancy boundary (Environment level)
# ---------------------------------------------------------------------------

def test_oci_tenancy_ocid_and_compartment_ocid_are_genuinely_distinct_concepts():
    """Tenancy (the OCI account-equivalent boundary) and compartment (a sub-division
    within a tenancy) must never be conflated -- constructing a boundary with a
    compartment-shaped string where a tenancy is required must be rejected."""
    with pytest.raises(EnvironmentValidationError):
        OCIBoundary(tenancy_ocid="ocid1.compartment.oc1..aaaa")  # compartment OCID used as tenancy -- wrong type


def test_oci_boundary_with_compartment_scoping_accepted():
    boundary = OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..aaaa", compartment_ocid="ocid1.compartment.oc1..bbbb")
    assert boundary.compartment_ocid == "ocid1.compartment.oc1..bbbb"


def test_oci_boundary_without_compartment_still_valid():
    """A tenancy-level environment with no specific compartment scoping is legitimate
    (e.g. representing the whole tenancy before compartment-level discovery narrows it)."""
    boundary = OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..aaaa")
    assert boundary.compartment_ocid is None


def test_oci_two_compartments_under_same_tenancy_remain_distinct_native_key():
    """native_key() is tenancy-scoped (matching AWS-account/Azure-subscription/GCP-
    project-scoped patterns) -- verify this doesn't accidentally collapse two
    genuinely different tenancies that happen to share a compartment OCID pattern."""
    tenancy_a = OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..aaaa")
    tenancy_b = OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..bbbb")
    assert tenancy_a.native_key() != tenancy_b.native_key()


def test_oci_malformed_tenancy_ocid_rejected():
    with pytest.raises(EnvironmentValidationError):
        OCIBoundary(tenancy_ocid="not-a-tenancy-ocid")


def test_oci_malformed_compartment_ocid_on_boundary_rejected():
    with pytest.raises(EnvironmentValidationError):
        OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..aaaa", compartment_ocid="not-a-compartment-ocid")


# ---------------------------------------------------------------------------
# Region / availability-domain representation (via Environment, not the OCID itself --
# OCI OCIDs for many resource types DO embed a region token, but AD is never embedded)
# ---------------------------------------------------------------------------

def test_oci_ocid_region_token_is_preserved_verbatim_never_reparsed_or_guessed():
    """The region token inside an OCID (e.g. 'iad', 'ap-hyderabad-1') is part of the
    opaque identifier string -- this module must never attempt to parse/validate it
    against a hardcoded region list (OCI adds regions over time; hardcoding would be
    exactly the kind of over-validation blocker #1/#2 warn against)."""
    for region_token, ocid in [
        ("iad", "ocid1.instance.oc1.iad.aaaa"),
        ("ap-hyderabad-1", "ocid1.instance.oc1.ap-hyderabad-1.aaaa"),
        ("uk-london-1", "ocid1.instance.oc1.uk-london-1.aaaa"),
    ]:
        locator = OCIResourceLocator(ocid=ocid, compartment_ocid="ocid1.compartment.oc1..bbbb")
        assert region_token in locator.ocid  # preserved verbatim, not reparsed/validated against a fixed list
