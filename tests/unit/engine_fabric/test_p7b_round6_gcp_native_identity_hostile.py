"""
tests.unit.engine_fabric.test_p7b_round6_gcp_native_identity_hostile
=========================================================================
P7B Group-1 Hostile Closure Round 6 -- GCP native-resource identity hostile matrix
(blocker #2). Covers project ID vs project number, organization/project relationships,
global/regional/zonal resource names, malformed names, cross-project substitution.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import EnvironmentValidationError, GCPBoundary
from akaalEngine.fabric.resource_identity import GCPResourceLocator, ResourceLocatorValidationError


# ---------------------------------------------------------------------------
# Cross-project substitution -- the real defect this file exists to expose/close
# ---------------------------------------------------------------------------

def test_gcp_project_id_prefix_collision_does_not_grant_cross_project_access():
    """CRITICAL: a resource actually belonging to project 'proj1-evil' must NEVER
    validate against a locator claiming project_id='proj1' merely because
    'projects/proj1' is a textual PREFIX of 'projects/proj1-evil/...'. This is a real
    substring-match defect class, not a hypothetical."""
    with pytest.raises(ResourceLocatorValidationError):
        GCPResourceLocator(resource_name="projects/proj1-evil/zones/us-central1-a/instances/victim-vm", project_id="proj1")


def test_gcp_project_id_suffix_collision_does_not_grant_cross_project_access():
    """The converse direction: a caller declaring project_id='proj1-evil' must not
    validate against a resource genuinely in 'proj1' either."""
    with pytest.raises(ResourceLocatorValidationError):
        GCPResourceLocator(resource_name="projects/proj1/zones/us-central1-a/instances/victim-vm", project_id="proj1-evil")


def test_gcp_correct_project_id_exact_match_still_accepted():
    locator = GCPResourceLocator(resource_name="projects/proj1/zones/us-central1-a/instances/my-vm", project_id="proj1")
    assert locator.project_id == "proj1"


# ---------------------------------------------------------------------------
# Project ID vs project number
# ---------------------------------------------------------------------------

def test_gcp_resource_locator_accepts_numeric_project_number_form():
    """Some GCP resource-name-returning APIs use the numeric project NUMBER instead of
    the human-readable project ID -- both are legitimate."""
    locator = GCPResourceLocator(resource_name="projects/123456789012/zones/us-central1-a/instances/my-vm", project_id="123456789012")
    assert locator.project_id == "123456789012"


def test_gcp_project_number_prefix_collision_also_blocked():
    with pytest.raises(ResourceLocatorValidationError):
        GCPResourceLocator(resource_name="projects/123456789012999/zones/us-central1-a/instances/vm", project_id="123456789012")


def test_gcp_boundary_project_id_and_project_number_are_distinct_forms_not_interchangeable():
    """Documented in Round 3: a project registered by ID string and referenced elsewhere
    by number are treated as distinct physical boundaries -- no silent equivalence."""
    by_id = GCPBoundary(project_id="my-real-project-1")
    by_number = GCPBoundary(project_id="123456789012")
    assert by_id.native_key() != by_number.native_key()


# ---------------------------------------------------------------------------
# Global / regional / zonal resource name shapes
# ---------------------------------------------------------------------------

def test_gcp_global_resource_name_accepted():
    """Global resources (e.g. a VPC network) have no region/zone segment at all."""
    locator = GCPResourceLocator(resource_name="projects/my-project/global/networks/default", project_id="my-project")
    assert "global/networks" in locator.resource_name


def test_gcp_regional_resource_name_accepted():
    locator = GCPResourceLocator(resource_name="projects/my-project/regions/asia-south1/subnetworks/subnet1", project_id="my-project")
    assert "regions/asia-south1" in locator.resource_name


def test_gcp_zonal_resource_name_accepted():
    locator = GCPResourceLocator(resource_name="projects/my-project/zones/asia-south1-a/instances/vm1", project_id="my-project")
    assert "zones/asia-south1-a" in locator.resource_name


# ---------------------------------------------------------------------------
# Organization / project relationship
# ---------------------------------------------------------------------------

def test_gcp_boundary_with_organization_context_accepted():
    boundary = GCPBoundary(project_id="my-project", organization_id="123456789")
    assert boundary.organization_id == "123456789"
    assert boundary.native_key() == ("GCP", "my-project")  # native_key is project-scoped, not org-scoped


def test_gcp_boundary_without_organization_context_still_valid():
    """Not every GCP project belongs to a visible organization (e.g. projects created
    outside an org) -- organization_id must remain genuinely optional."""
    boundary = GCPBoundary(project_id="my-project")
    assert boundary.organization_id is None


def test_gcp_two_projects_under_same_organization_remain_distinct_boundaries():
    proj_a = GCPBoundary(project_id="project-a", organization_id="999999999")
    proj_b = GCPBoundary(project_id="project-b", organization_id="999999999")
    assert proj_a.native_key() != proj_b.native_key()


# ---------------------------------------------------------------------------
# Malformed names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("malformed_name", [
    "not-a-resource-name",
    "",
    "projects",  # no slash at all after "projects"
])
def test_gcp_malformed_resource_names_rejected(malformed_name):
    with pytest.raises(ResourceLocatorValidationError):
        GCPResourceLocator(resource_name=malformed_name, project_id="my-project")


@pytest.mark.parametrize("bad_project_id", ["", "UPPERCASE-BAD", "ab", "-starts-with-hyphen"])
def test_gcp_boundary_malformed_project_ids_rejected(bad_project_id):
    with pytest.raises(EnvironmentValidationError):
        GCPBoundary(project_id=bad_project_id)
