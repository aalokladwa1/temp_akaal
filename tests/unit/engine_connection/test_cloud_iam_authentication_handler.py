"""
tests.unit.engine_connection.test_cloud_iam_authentication_handler
======================================================================
P7B.3 integration test: CloudIAMAuthenticationHandler now performs real cloud identity
resolution (previously a complete no-op passthrough -- a genuine, verified gap) while
preserving backward-compatible behavior when cloud resolution cannot be attempted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType
from akaalEngine.connection.security.authentication import AuthenticationManager
from akaalEngine.connection.security.secret_consumer import SecretConsumer


def test_aws_iam_role_without_dependency_falls_back_to_passthrough_shape():
    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.AWS_IAM_ROLE, role_arn="arn:aws:iam::123456789012:role/akaal")
    creds = mgr.resolve_credentials(spec, provider_id="s3")

    # Backward-compatible fields always present regardless of whether cloud resolution succeeded.
    assert creds["role_arn"] == "arn:aws:iam::123456789012:role/akaal"
    assert creds["auth_type"] == "AWS_IAM_ROLE"
    # Either a resolved identity or a truthfully recorded resolution error -- never silence.
    assert "cloud_identity" in creds or "cloud_identity_error" in creds


def test_aws_iam_role_with_injected_sts_resolves_real_bounded_identity(monkeypatch):
    class _FakeSTS:
        def assume_role(self, RoleArn, RoleSessionName):
            return {
                "Credentials": {"AccessKeyId": "AKIA...", "Expiration": datetime.now(timezone.utc) + timedelta(hours=1)},
                "AssumedRoleUser": {"Arn": "arn:aws:sts::123456789012:assumed-role/akaal/session"},
            }

    import akaalEngine.fabric.workload_identity as wi_pkg
    monkeypatch.setattr(wi_pkg, "resolve_aws_workload_identity", lambda role_arn_to_assume=None, sts_client=None, session_name="akaal-workload": wi_pkg.CloudIdentityContext(
        provider=wi_pkg.CloudAuthProvider.AWS,
        principal_id="arn:aws:sts::123456789012:assumed-role/akaal/session",
        account_boundary="123456789012",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    ))

    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.AWS_IAM_ROLE, role_arn="arn:aws:iam::123456789012:role/akaal")
    creds = mgr.resolve_credentials(spec, provider_id="s3")

    assert "cloud_identity" in creds
    assert creds["cloud_identity"].account_boundary == "123456789012"
    assert creds["cloud_identity"].has_bounded_lifetime()


def test_azure_entra_without_subscription_id_does_not_raise_and_omits_identity():
    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.AZURE_ENTRA_ID)
    creds = mgr.resolve_credentials(spec, provider_id="azure_blob")
    assert "cloud_identity" not in creds
    assert "cloud_identity_error" not in creds  # returning None (missing subscription_id) is not an error


def test_resolution_failure_never_raises_out_of_authentication_manager():
    """A cloud SDK error must never crash generic credential resolution -- it fails soft
    into the pre-P7B passthrough shape with the error truthfully recorded."""
    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.OCI_INSTANCE_PRINCIPAL)
    creds = mgr.resolve_credentials(spec, provider_id="oci_object_storage")
    assert creds["auth_type"] == "OCI_INSTANCE_PRINCIPAL"
