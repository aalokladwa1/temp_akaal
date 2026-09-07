"""
tests.unit.engine_fabric.test_p7b_1_environment_model
========================================================
P7B.1 hostile tests -- canonical Environment model + registry.

Proves the explicit security invariants required by P7B Group 1 §1:
  * malformed environment rejected
  * duplicate identity handled deterministically
  * cross-tenant environment cannot be claimed by locator alone
  * unknown environment fails safely
  * provider-specific identity preserved (no false normalization)
  * environment ID cannot establish authorization
  * impossible/inconsistent topology fails rather than silently normalizing
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import (
    AWSBoundary,
    AzureBoundary,
    Environment,
    EnvironmentLifecycleState,
    EnvironmentRegistry,
    EnvironmentTrustState,
    EnvironmentType,
    EnvironmentValidationError,
    DuplicateEnvironmentIdentityError,
    UnknownEnvironmentError,
    GCPBoundary,
    OCIBoundary,
    new_environment_id,
)


def _aws_env(env_id: str = None, account_id: str = "123456789012") -> Environment:
    return Environment(
        environment_id=env_id or new_environment_id(EnvironmentType.AWS),
        environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary(account_id=account_id),
        region="us-east-1",
    )


def test_malformed_aws_account_id_rejected():
    with pytest.raises(EnvironmentValidationError):
        AWSBoundary(account_id="not-a-valid-account")

    with pytest.raises(EnvironmentValidationError):
        AWSBoundary(account_id="123")  # too short


def test_malformed_azure_subscription_id_rejected():
    with pytest.raises(EnvironmentValidationError):
        AzureBoundary(subscription_id="not-a-uuid")


def test_malformed_oci_tenancy_ocid_rejected():
    with pytest.raises(EnvironmentValidationError):
        OCIBoundary(tenancy_ocid="not-an-ocid")


def test_empty_environment_id_rejected():
    with pytest.raises(EnvironmentValidationError):
        Environment(environment_id="", environment_type=EnvironmentType.AWS, boundary=AWSBoundary("123456789012"))


def test_impossible_topology_boundary_mismatch_fails_rather_than_normalizing():
    """An AWS-typed Environment must not silently accept an Azure boundary."""
    azure_boundary = AzureBoundary(subscription_id="11111111-1111-1111-1111-111111111111")
    with pytest.raises(EnvironmentValidationError):
        Environment(environment_id="env-x", environment_type=EnvironmentType.AWS, boundary=azure_boundary)


def test_provider_specific_identity_never_falsely_normalized():
    """AWS account != Azure subscription != GCP project != OCI tenancy -- distinct types."""
    aws = AWSBoundary(account_id="123456789012")
    azure = AzureBoundary(subscription_id="11111111-1111-1111-1111-111111111111")
    gcp = GCPBoundary(project_id="my-gcp-project-1")
    oci = OCIBoundary(tenancy_ocid="ocid1.tenancy.oc1..aaaaaaaa")

    assert type(aws) is not type(azure)
    assert aws.native_key()[0] == "AWS"
    assert azure.native_key()[0] == "AZURE"
    assert gcp.native_key()[0] == "GCP"
    assert oci.native_key()[0] == "OCI"
    # No shared generic field name across boundary types
    assert not hasattr(aws, "subscription_id")
    assert not hasattr(azure, "account_id")


def test_registration_does_not_grant_authorization_or_elevate_trust():
    """Environment ID / registration is a locator, not authorization; trust defaults UNKNOWN."""
    registry = EnvironmentRegistry()
    env = _aws_env()
    registered = registry.register(env)

    assert registered.trust_state == EnvironmentTrustState.UNKNOWN
    # There is no "is_authorized" or "grants" attribute anywhere on Environment --
    # authorization is exclusively akaalPipeline.security.central_authorization's concern.
    assert not hasattr(registered, "is_authorized")
    assert not hasattr(registered, "grants")


def test_duplicate_environment_id_with_different_boundary_rejected_deterministically():
    registry = EnvironmentRegistry()
    env_id = "env-shared-id"
    registry.register(_aws_env(env_id=env_id, account_id="123456789012"))

    with pytest.raises(DuplicateEnvironmentIdentityError):
        registry.register(_aws_env(env_id=env_id, account_id="999999999999"))


def test_same_physical_boundary_cannot_be_registered_under_a_second_locator():
    """Cross-tenant / locator-shopping attack: same physical resource, fresh untrusted id."""
    registry = EnvironmentRegistry()
    registry.register(_aws_env(env_id="env-original", account_id="123456789012"))

    with pytest.raises(DuplicateEnvironmentIdentityError):
        registry.register(_aws_env(env_id="env-attacker-claimed", account_id="123456789012"))


def test_idempotent_reregistration_of_identical_environment_succeeds():
    registry = EnvironmentRegistry()
    env = _aws_env(env_id="env-idempotent", account_id="123456789012")
    registry.register(env)
    # Re-registering the exact same (id, boundary) pair must not raise.
    registry.register(env)


def test_unknown_environment_fails_safely_not_silently():
    registry = EnvironmentRegistry()
    with pytest.raises(UnknownEnvironmentError):
        registry.get("env-does-not-exist")

    assert registry.try_get("env-does-not-exist") is None


def test_jurisdiction_is_never_inferred_defaults_to_none():
    env = _aws_env()
    assert env.jurisdiction is None
    # Region alone must never silently become a jurisdiction claim.
    env_with_region = Environment(
        environment_id=new_environment_id(EnvironmentType.AWS),
        environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary("123456789012"),
        region="eu-west-1",
    )
    assert env_with_region.jurisdiction is None


def test_trust_elevation_is_explicit_auditable_and_requires_reason():
    registry = EnvironmentRegistry()
    env = _aws_env(env_id="env-trust-test")
    registry.register(env)

    with pytest.raises(Exception):
        registry.elevate_trust("env-trust-test", EnvironmentTrustState.VERIFIED, reason="")

    updated = registry.elevate_trust("env-trust-test", EnvironmentTrustState.VERIFIED, reason="manual owner review")
    assert updated.trust_state == EnvironmentTrustState.VERIFIED
    # Original registered object is immutable and unaffected.
    assert env.trust_state == EnvironmentTrustState.UNKNOWN


def test_environment_networks_and_capabilities_are_immutable():
    from akaalEngine.fabric.environment import NetworkSubnet

    env = Environment(
        environment_id=new_environment_id(EnvironmentType.AWS),
        environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary("123456789012"),
        networks=(NetworkSubnet(subnet_id="subnet-1", cidr="10.0.0.0/24"),),
        capabilities={"OBJECT_STORAGE", "COMPUTE"},
    )
    assert isinstance(env.networks, tuple)
    assert isinstance(env.capabilities, frozenset)
    with pytest.raises(Exception):
        env.networks = ()  # frozen dataclass


def test_lifecycle_state_defaults_provisional_not_active():
    env = _aws_env()
    assert env.lifecycle_state == EnvironmentLifecycleState.PROVISIONAL
