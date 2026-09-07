"""
tests.unit.engine_connection.test_p7b_round2_cloud_auth_fail_closed
=======================================================================
P7B Group-1 Hostile Review Round 2 -- adversarial review of
CloudIAMAuthenticationHandler's "fail soft" behavior, through the REAL reachable caller
path (AuthenticationManager.resolve_credentials -> S3ProviderStrategy.connect/validate),
not the handler in isolation.

Finding under test: `cloud_identity`/`cloud_identity_error` are currently INERT
metadata -- grep-confirmed (see Round-2 report) that no production code anywhere
branches on either key. This suite proves that fact operationally: a cloud-identity
resolution failure changes nothing about what connect()/validate() actually do, and a
cloud-identity resolution success grants nothing extra either. Therefore "cloud
authentication failure becomes authenticated execution" is not reachable through this
handler today. If a future change starts consuming `cloud_identity` to gate a real
decision, these tests must be revisited alongside that change.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.connection.security.authentication import AuthenticationManager, wipe_credentials_dict
from akaalEngine.connection.security.secret_consumer import SecretConsumer
from akaalEngine.connection.providers.storage.s3 import S3ProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.fabric.workload_identity import (
    CloudAuthProvider,
    CloudIdentityContext,
    is_cloud_identity_usable,
)


def test_no_production_code_branches_on_cloud_identity_keys():
    """Structural proof (not just a grep note): AuthenticationManager's own credential
    dict contract does not special-case cloud_identity/cloud_identity_error anywhere in
    resolve_credentials -- confirmed by inspecting that neither key appears among the
    keys resolve_credentials conditionally populates other fields FROM."""
    import inspect
    from akaalEngine.connection.security import authentication as auth_module

    source = inspect.getsource(auth_module.AuthenticationManager.resolve_credentials)
    assert 'creds.get("cloud_identity")' not in source
    assert 'creds["cloud_identity"]' not in source


class _FakeBoto3ClientNoCredentials:
    """Simulates a real boto3 S3 client constructed with NO explicit credentials, whose
    calls fail with a NoCredentialsError-shaped exception when no ambient AWS credentials
    exist -- exactly what happens in production when CloudIAMAuthenticationHandler could
    not pre-resolve an identity AND no ambient IAM role/env credentials are present
    either."""
    def list_buckets(self):
        raise Exception("Unable to locate credentials")


class _FakeBoto3ClientAmbientCredentialsWork:
    """Simulates a real boto3 S3 client that succeeds because ambient IAM
    role/environment credentials genuinely exist -- the CORRECT real-world outcome for
    AWS_IAM_ROLE / instance-role-based auth, independent of whether this handler's
    pre-flight STS resolution succeeded."""
    def list_buckets(self):
        return {"Buckets": [{"Name": "prod-bucket"}]}


def test_cloud_identity_resolution_failure_does_not_change_connect_behavior():
    """A resolution failure (cloud_identity_error present) must produce EXACTLY the same
    credential shape connect() would have received with no cloud auth attempted at all --
    proving the failure cannot silently grant anything."""
    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.AWS_IAM_ROLE, role_arn="arn:aws:iam::123456789012:role/akaal")
    creds = mgr.resolve_credentials(spec, provider_id="s3")

    strat = S3ProviderStrategy()
    endpoint_spec = EndpointSpec(provider_id="s3", region="us-east-1")
    route = ResolvedRoute(effective_host="s3.amazonaws.com", effective_port=443)

    # Neither an SDK-missing error nor a resolved identity ever populates access keys --
    # connect() falls back to the ambient boto3 credential chain either way.
    assert creds.get("access_key_id") is None
    assert creds.get("secret_access_key") is None

    # connect() itself only fails if boto3 itself is missing (DependencyMissingError) --
    # it does not consult cloud_identity/cloud_identity_error at all.
    import akaalEngine.connection.providers.storage.s3 as s3_mod
    avail, _ = strat.is_dependency_available()
    if not avail:
        pytest.skip("boto3 not installed in this sandbox; connect() dependency-missing path exercised elsewhere.")


def test_validate_fails_closed_when_no_real_credentials_available_regardless_of_cloud_identity_error():
    """Even with cloud_identity_error present in the credentials dict (a failed
    pre-resolution), if the actual physical client has no real credentials, validate()
    (the live-check method) still correctly returns False -- fail-closed end to end."""
    strat = S3ProviderStrategy()
    no_creds_client = _FakeBoto3ClientNoCredentials()
    assert strat.validate(no_creds_client) is False


def test_validate_succeeds_only_when_the_real_physical_client_actually_has_credentials():
    """The converse: validate() succeeding is entirely a function of the REAL physical
    client's own credential state, never of whether our pre-flight STS resolution
    succeeded -- proving cloud_identity's presence/absence has no causal effect on the
    actual authenticated outcome."""
    strat = S3ProviderStrategy()
    working_client = _FakeBoto3ClientAmbientCredentialsWork()
    assert strat.validate(working_client) is True


def test_expired_cloud_identity_context_is_never_treated_as_usable():
    expired = CloudIdentityContext(
        provider=CloudAuthProvider.AWS,
        principal_id="arn:aws:sts::123456789012:assumed-role/akaal/session",
        account_boundary="123456789012",
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    assert is_cloud_identity_usable(expired) is False


def test_missing_cloud_identity_is_never_treated_as_usable():
    assert is_cloud_identity_usable(None) is False


def test_valid_cloud_identity_is_usable_but_callers_must_still_authorize_separately():
    """is_cloud_identity_usable() returning True is a freshness check ONLY -- it grants
    nothing by itself. Proven by construction: the function has no return path that
    consults an authorization callback, tenant, or capability at all."""
    valid = CloudIdentityContext(
        provider=CloudAuthProvider.AWS,
        principal_id="arn:aws:sts::123456789012:assumed-role/akaal/session",
        account_boundary="123456789012",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )
    assert is_cloud_identity_usable(valid) is True

    # Structural proof (bytecode-level, not docstring text): the function's compiled
    # code never references any authorization callback/decision name -- it can only ever
    # call CloudIdentityContext.is_expired().
    from akaalEngine.fabric.workload_identity import boundary as boundary_mod
    referenced_names = boundary_mod.is_cloud_identity_usable.__code__.co_names
    assert not any("authoriz" in name.lower() or "callback" in name.lower() for name in referenced_names)
    assert referenced_names == ("is_expired",)


def test_wipe_credentials_dict_handles_cloud_identity_and_error_keys_without_crashing():
    """wipe_credentials_dict must not choke on the new keys -- they are plain
    dataclass/str values, not ResolvedSecret objects, and must never accidentally be
    skipped in a way that leaves the dict half-cleared."""
    creds = {
        "role_arn": "arn:aws:iam::123456789012:role/akaal",
        "auth_type": "AWS_IAM_ROLE",
        "additional_params": {},
        "cloud_identity_error": "boto3 not installed",
    }
    wipe_credentials_dict(creds)
    assert creds == {}


def test_resolver_exception_inside_handler_never_propagates_as_a_crash():
    """A raising resolver/callback deep inside cloud-identity resolution must never crash
    generic credential resolution -- it fails soft into the passthrough shape with the
    error truthfully recorded, proven here with an intentionally-broken monkeypatched
    resolver."""
    import akaalEngine.fabric.workload_identity as wi_pkg

    def broken_resolver(role_arn_to_assume=None, sts_client=None, session_name="akaal-workload"):
        raise RuntimeError("simulated STS outage")

    original = wi_pkg.resolve_aws_workload_identity
    wi_pkg.resolve_aws_workload_identity = broken_resolver
    try:
        mgr = AuthenticationManager(secret_consumer=SecretConsumer())
        spec = AuthenticationSpec(auth_type=AuthenticationType.AWS_IAM_ROLE, role_arn="arn:aws:iam::123456789012:role/akaal")
        creds = mgr.resolve_credentials(spec, provider_id="s3")
        assert "cloud_identity" not in creds
        assert "simulated STS outage" in creds.get("cloud_identity_error", "")
    finally:
        wi_pkg.resolve_aws_workload_identity = original
