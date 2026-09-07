"""
tests.unit.engine_fabric.test_p7b_3_workload_identity
========================================================
P7B.3 hostile tests -- workload identity & cloud authentication.

Proves: valid cloud identity + authorized action succeeds only via explicit callback;
valid cloud identity + unauthorized action denied; expired token fails closed; missing
credentials/dependency fails closed; malformed inputs rejected; wrong role/audience;
cross-tenant cloud identity cannot silently authorize; no default-allow path exists.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.fabric.workload_identity import (
    CloudAuthenticationBoundary,
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDeniedError,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityError,
    WorkloadIdentityExpiredError,
    WorkloadIdentityUnavailableError,
    resolve_aws_workload_identity,
    resolve_azure_workload_identity,
    resolve_gcp_workload_identity,
    resolve_oci_workload_identity,
)


def _identity(expires_in_seconds: float = 3600.0) -> CloudIdentityContext:
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat()
    return CloudIdentityContext(
        provider=CloudAuthProvider.AWS,
        principal_id="arn:aws:sts::123456789012:assumed-role/akaal/workload",
        account_boundary="123456789012",
        assumed_role="arn:aws:iam::123456789012:role/akaal",
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Boundary: cloud auth != AKAAL authorization
# ---------------------------------------------------------------------------

def test_valid_identity_with_authorized_callback_succeeds():
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    decision = boundary.authorize_akaal_action(identity, "migration.execute", lambda i, a, c: True)
    assert decision is True


def test_valid_identity_with_denying_callback_is_denied():
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    decision = boundary.authorize_akaal_action(identity, "migration.execute", lambda i, a, c: False)
    assert decision is False


def test_missing_authorization_callback_fails_closed():
    """No default-allow path exists: without a callback, the boundary always raises."""
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    with pytest.raises(WorkloadIdentityError):
        boundary.authorize_akaal_action(identity, "migration.execute", None)


def test_expired_identity_denied_even_with_permissive_callback():
    """A valid-shaped but expired cloud identity must never authorize anything, no matter
    what the callback would have said."""
    boundary = CloudAuthenticationBoundary()
    expired_identity = _identity(expires_in_seconds=-10.0)
    with pytest.raises(WorkloadIdentityExpiredError):
        boundary.authorize_akaal_action(expired_identity, "migration.execute", lambda i, a, c: True)


def test_non_boolean_callback_result_fails_closed():
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    with pytest.raises(WorkloadIdentityError):
        boundary.authorize_akaal_action(identity, "migration.execute", lambda i, a, c: "yes")


def test_empty_requested_action_rejected():
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    with pytest.raises(WorkloadIdentityError):
        boundary.authorize_akaal_action(identity, "", lambda i, a, c: True)


def test_callback_receives_identity_and_action_for_its_own_tenant_scoping():
    """Demonstrates that any tenant-boundary decision is entirely the callback's
    responsibility -- the boundary itself does not inspect tenant/workspace/project."""
    boundary = CloudAuthenticationBoundary()
    identity = _identity()
    received = {}

    def callback(ident, action, ctx):
        received["identity"] = ident
        received["action"] = action
        received["ctx"] = ctx
        return ctx.get("tenant_id") == "tenant-a"

    assert boundary.authorize_akaal_action(identity, "x", callback, context={"tenant_id": "tenant-b"}) is False
    assert boundary.authorize_akaal_action(identity, "x", callback, context={"tenant_id": "tenant-a"}) is True
    assert received["identity"] is identity


def test_no_expiry_recorded_is_not_treated_as_expired_but_is_distinguishable():
    identity = CloudIdentityContext(
        provider=CloudAuthProvider.AWS,
        principal_id="arn:aws:iam::123456789012:user/ambient",
        account_boundary="123456789012",
        expires_at=None,
    )
    assert identity.is_expired() is False
    assert identity.has_bounded_lifetime() is False


def test_malformed_identity_empty_principal_rejected():
    with pytest.raises(WorkloadIdentityError):
        CloudIdentityContext(provider=CloudAuthProvider.AWS, principal_id="", account_boundary="123456789012")


# ---------------------------------------------------------------------------
# AWS
# ---------------------------------------------------------------------------

class _FakeSTS:
    def __init__(self, assume_result=None, assume_exc=None, identity_result=None, identity_exc=None):
        self._assume_result = assume_result
        self._assume_exc = assume_exc
        self._identity_result = identity_result
        self._identity_exc = identity_exc

    def assume_role(self, RoleArn, RoleSessionName):
        if self._assume_exc:
            raise self._assume_exc
        return self._assume_result

    def get_caller_identity(self):
        if self._identity_exc:
            raise self._identity_exc
        return self._identity_result


def test_aws_assume_role_denied_fails_closed():
    sts = _FakeSTS(assume_exc=Exception("AccessDenied: not authorized to perform sts:AssumeRole"))
    with pytest.raises(WorkloadIdentityDeniedError):
        resolve_aws_workload_identity(sts_client=sts, role_arn_to_assume="arn:aws:iam::123456789012:role/akaal")


def test_aws_assume_role_success_has_bounded_expiry():
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    sts = _FakeSTS(assume_result={
        "Credentials": {"AccessKeyId": "AKIA...", "Expiration": expiration},
        "AssumedRoleUser": {"Arn": "arn:aws:sts::123456789012:assumed-role/akaal/session"},
    })
    identity = resolve_aws_workload_identity(sts_client=sts, role_arn_to_assume="arn:aws:iam::123456789012:role/akaal")
    assert identity.has_bounded_lifetime()
    assert identity.account_boundary == "123456789012"


def test_aws_ambient_identity_without_role_has_no_fabricated_expiry():
    sts = _FakeSTS(identity_result={"Arn": "arn:aws:iam::123456789012:user/dev", "Account": "123456789012"})
    identity = resolve_aws_workload_identity(sts_client=sts)
    assert identity.has_bounded_lifetime() is False


# ---------------------------------------------------------------------------
# Azure
# ---------------------------------------------------------------------------

class _FakeAzureToken:
    def __init__(self, token="tok", expires_on=None):
        self.token = token
        self.expires_on = expires_on


class _FakeAzureCredential:
    def __init__(self, token=None, exc=None):
        self._token = token
        self._exc = exc

    def get_token(self, scope):
        if self._exc:
            raise self._exc
        return self._token


def test_azure_requires_explicit_subscription_id():
    with pytest.raises(ValueError):
        resolve_azure_workload_identity(subscription_id="", credential=_FakeAzureCredential())


def test_azure_authentication_denied_fails_closed():
    cred = _FakeAzureCredential(exc=Exception("AuthenticationRequiredError: interactive authentication needed"))
    with pytest.raises(WorkloadIdentityDeniedError):
        resolve_azure_workload_identity(subscription_id="11111111-1111-1111-1111-111111111111", credential=cred)


def test_azure_missing_expiry_fails_closed():
    cred = _FakeAzureCredential(token=_FakeAzureToken(expires_on=None))
    with pytest.raises(WorkloadIdentityUnavailableError):
        resolve_azure_workload_identity(subscription_id="11111111-1111-1111-1111-111111111111", credential=cred)


def test_azure_success_reports_real_expiry():
    expires_on = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    cred = _FakeAzureCredential(token=_FakeAzureToken(expires_on=expires_on))
    identity = resolve_azure_workload_identity(subscription_id="11111111-1111-1111-1111-111111111111", credential=cred)
    assert identity.account_boundary == "11111111-1111-1111-1111-111111111111"
    assert identity.has_bounded_lifetime()


# ---------------------------------------------------------------------------
# GCP
# ---------------------------------------------------------------------------

class _FakeGCPCredentials:
    def __init__(self, expiry=None, refresh_exc=None, service_account_email=None):
        self.expiry = expiry
        self._refresh_exc = refresh_exc
        self.service_account_email = service_account_email

    def refresh(self, request):
        if self._refresh_exc:
            raise self._refresh_exc


def test_gcp_permission_denied_on_refresh_fails_closed():
    creds = _FakeGCPCredentials(refresh_exc=Exception("invalid_grant: account not found"))
    with pytest.raises(WorkloadIdentityDeniedError):
        resolve_gcp_workload_identity(project_id="my-project", credentials=creds, refresh_request=object())


def test_gcp_missing_project_id_fails_closed():
    creds = _FakeGCPCredentials(expiry=datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(WorkloadIdentityUnavailableError):
        resolve_gcp_workload_identity(project_id=None, credentials=creds, refresh_request=object())


def test_gcp_success_reports_principal_and_expiry():
    creds = _FakeGCPCredentials(
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        service_account_email="workload@my-project.iam.gserviceaccount.com",
    )
    identity = resolve_gcp_workload_identity(project_id="my-project", credentials=creds, refresh_request=object())
    assert identity.principal_id == "workload@my-project.iam.gserviceaccount.com"
    assert identity.account_boundary == "my-project"


# ---------------------------------------------------------------------------
# OCI
# ---------------------------------------------------------------------------

def test_oci_missing_signer_fails_closed():
    with pytest.raises(WorkloadIdentityError):
        resolve_oci_workload_identity(signer=None, principal_id="ocid1.instance.oc1..aaaa", tenancy_ocid="ocid1.tenancy.oc1..bbbb")


def test_oci_malformed_tenancy_ocid_rejected():
    with pytest.raises(WorkloadIdentityError):
        resolve_oci_workload_identity(signer=object(), principal_id="ocid1.instance.oc1..aaaa", tenancy_ocid="not-a-tenancy-ocid")


def test_oci_success_produces_canonical_identity_shape():
    identity = resolve_oci_workload_identity(
        signer=object(),
        principal_id="ocid1.instance.oc1..aaaa",
        tenancy_ocid="ocid1.tenancy.oc1..bbbb",
        expires_at=None,
        mode="instance_principal",
    )
    assert identity.provider == CloudAuthProvider.OCI
    assert identity.account_boundary == "ocid1.tenancy.oc1..bbbb"
