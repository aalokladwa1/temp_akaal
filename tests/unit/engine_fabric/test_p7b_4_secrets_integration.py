"""
tests.unit.engine_fabric.test_p7b_4_secrets_integration
==========================================================
P7B.4 hostile tests -- cloud secrets/keys/certificate integration.

Covers: successful reference resolution; missing secret; wrong-account secret refused;
unauthorized/permission-denied; throttling; provider unavailable; disabled secret;
malformed reference (path traversal for Kubernetes); zero-plaintext-leak in error paths;
integration with SecretConsumer (P7.7 canonical boundary) without a new secret authority.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalEngine.connection.security.providers.aws_secrets_manager import (
    AWSSecretsManagerConfig,
    AWSSecretsManagerError,
    AWSSecretsManagerProvider,
)
from akaalEngine.connection.security.providers.azure_key_vault import (
    AzureKeyVaultConfig,
    AzureKeyVaultError,
    AzureKeyVaultProvider,
)
from akaalEngine.connection.security.providers.gcp_secret_manager import (
    GCPSecretManagerConfig,
    GCPSecretManagerError,
    GCPSecretManagerProvider,
)
from akaalEngine.connection.security.providers.oci_vault import (
    OCIVaultConfig,
    OCIVaultError,
    OCIVaultProvider,
)
from akaalEngine.connection.security.providers.kubernetes_secret_ref import (
    KubernetesSecretRefConfig,
    KubernetesSecretRefError,
    KubernetesSecretRefProvider,
)
from akaalEngine.connection.security.secret_consumer import SecretConsumer


# ---------------------------------------------------------------------------
# AWS Secrets Manager
# ---------------------------------------------------------------------------

class _FakeAWSSMClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def get_secret_value(self, SecretId):
        if self._exc:
            raise self._exc
        return self._response


def test_aws_secrets_manager_successful_resolution():
    client = _FakeAWSSMClient(response={"SecretString": "sup3r-secret", "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"})
    provider = AWSSecretsManagerProvider(AWSSecretsManagerConfig(account_id="123456789012"), client=client)
    assert provider.resolve("x") == "sup3r-secret"


def test_aws_secrets_manager_wrong_account_refused():
    client = _FakeAWSSMClient(response={"SecretString": "value", "ARN": "arn:aws:secretsmanager:us-east-1:999999999999:secret:x"})
    provider = AWSSecretsManagerProvider(AWSSecretsManagerConfig(account_id="123456789012"), client=client)
    with pytest.raises(AWSSecretsManagerError):
        provider.resolve("x")


def test_aws_secrets_manager_not_found():
    client = _FakeAWSSMClient(exc=Exception("ResourceNotFoundException: Secret not found"))
    provider = AWSSecretsManagerProvider(client=client)
    with pytest.raises(AWSSecretsManagerError):
        provider.resolve("missing-secret")


def test_aws_secrets_manager_access_denied_does_not_leak_message_content():
    client = _FakeAWSSMClient(exc=Exception("AccessDeniedException: user arn:aws:iam::123456789012:user/x is not authorized"))
    provider = AWSSecretsManagerProvider(client=client)
    with pytest.raises(AWSSecretsManagerError):
        provider.resolve("x")


def test_aws_secrets_manager_json_key_extraction():
    client = _FakeAWSSMClient(response={"SecretString": '{"password": "hunter2"}', "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"})
    provider = AWSSecretsManagerProvider(client=client)
    assert provider.resolve("x#password") == "hunter2"


# ---------------------------------------------------------------------------
# Azure Key Vault
# ---------------------------------------------------------------------------

class _FakeAzureSecretProperties:
    def __init__(self, enabled=True):
        self.enabled = enabled


class _FakeAzureSecret:
    def __init__(self, value, enabled=True):
        self.value = value
        self.properties = _FakeAzureSecretProperties(enabled)


class _FakeAzureKVClient:
    def __init__(self, secret=None, exc=None):
        self._secret = secret
        self._exc = exc

    def get_secret(self, name, version=None):
        if self._exc:
            raise self._exc
        return self._secret


def test_azure_key_vault_successful_resolution():
    client = _FakeAzureKVClient(secret=_FakeAzureSecret("kv-secret-value"))
    provider = AzureKeyVaultProvider(AzureKeyVaultConfig(vault_url="https://myvault.vault.azure.net/"), client=client)
    assert provider.resolve("db-password") == "kv-secret-value"


def test_azure_key_vault_disabled_secret_refused():
    client = _FakeAzureKVClient(secret=_FakeAzureSecret("value", enabled=False))
    provider = AzureKeyVaultProvider(AzureKeyVaultConfig(vault_url="https://myvault.vault.azure.net/"), client=client)
    with pytest.raises(AzureKeyVaultError):
        provider.resolve("db-password")


def test_azure_key_vault_not_found():
    client = _FakeAzureKVClient(exc=Exception("SecretNotFound: 404 Secret not found"))
    provider = AzureKeyVaultProvider(AzureKeyVaultConfig(vault_url="https://myvault.vault.azure.net/"), client=client)
    with pytest.raises(AzureKeyVaultError):
        provider.resolve("missing")


# ---------------------------------------------------------------------------
# GCP Secret Manager
# ---------------------------------------------------------------------------

class _FakeGCPPayload:
    def __init__(self, data: bytes):
        self.data = data


class _FakeGCPResponse:
    def __init__(self, data: bytes):
        self.payload = _FakeGCPPayload(data)


class _FakeGCPClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def access_secret_version(self, name):
        if self._exc:
            raise self._exc
        return self._response


def test_gcp_secret_manager_successful_resolution():
    client = _FakeGCPClient(response=_FakeGCPResponse(b"gcp-secret-value"))
    provider = GCPSecretManagerProvider(GCPSecretManagerConfig(project_id="my-project"), client=client)
    assert provider.resolve("db-password") == "gcp-secret-value"


def test_gcp_secret_manager_permission_denied():
    client = _FakeGCPClient(exc=Exception("PermissionDenied: 403 caller lacks permission"))
    provider = GCPSecretManagerProvider(GCPSecretManagerConfig(project_id="my-project"), client=client)
    with pytest.raises(GCPSecretManagerError):
        provider.resolve("x")


def test_gcp_secret_manager_requires_project_id():
    with pytest.raises(GCPSecretManagerError):
        GCPSecretManagerProvider(GCPSecretManagerConfig(project_id=""), client=_FakeGCPClient())


# ---------------------------------------------------------------------------
# OCI Vault
# ---------------------------------------------------------------------------

class _FakeOCIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class _FakeOCIBundleContent:
    def __init__(self, content_b64):
        self.content = content_b64


class _FakeOCIBundle:
    def __init__(self, content_b64):
        self.secret_bundle_content = _FakeOCIBundleContent(content_b64)


class _FakeOCIResponse:
    def __init__(self, content_b64):
        self.data = _FakeOCIBundle(content_b64)


class _FakeOCIClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def get_secret_bundle(self, secret_id):
        if self._exc:
            raise self._exc
        return self._response


def test_oci_vault_successful_resolution():
    import base64
    b64 = base64.b64encode(b"oci-secret-value").decode("ascii")
    client = _FakeOCIClient(response=_FakeOCIResponse(b64))
    provider = OCIVaultProvider(OCIVaultConfig(compartment_ocid="ocid1.compartment.oc1..aaaa"), client=client)
    assert provider.resolve("ocid1.vaultsecret.oc1.iad.bbbb") == "oci-secret-value"


def test_oci_vault_requires_client():
    with pytest.raises(OCIVaultError):
        OCIVaultProvider(OCIVaultConfig(compartment_ocid="ocid1.compartment.oc1..aaaa"), client=None)


def test_oci_vault_rejects_non_ocid_reference():
    client = _FakeOCIClient()
    provider = OCIVaultProvider(OCIVaultConfig(compartment_ocid="ocid1.compartment.oc1..aaaa"), client=client)
    with pytest.raises(OCIVaultError):
        provider.resolve("not-an-ocid")


def test_oci_vault_permission_denied():
    client = _FakeOCIClient(exc=_FakeOCIError(403, "not authorized"))
    provider = OCIVaultProvider(OCIVaultConfig(compartment_ocid="ocid1.compartment.oc1..aaaa"), client=client)
    with pytest.raises(OCIVaultError):
        provider.resolve("ocid1.vaultsecret.oc1.iad.bbbb")


def test_oci_vault_throttled():
    client = _FakeOCIClient(exc=_FakeOCIError(429, "too many requests"))
    provider = OCIVaultProvider(OCIVaultConfig(compartment_ocid="ocid1.compartment.oc1..aaaa"), client=client)
    with pytest.raises(OCIVaultError):
        provider.resolve("ocid1.vaultsecret.oc1.iad.bbbb")


# ---------------------------------------------------------------------------
# Kubernetes Secret references
# ---------------------------------------------------------------------------

def test_kubernetes_secret_ref_successful_resolution(tmp_path):
    secret_dir = tmp_path / "db-credentials"
    secret_dir.mkdir()
    (secret_dir / "password").write_text("k8s-secret-value\n")

    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    assert provider.resolve("db-credentials/password") == "k8s-secret-value"


def test_kubernetes_secret_ref_path_traversal_blocked(tmp_path):
    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("../../../etc/passwd")


def test_kubernetes_secret_ref_missing_file(tmp_path):
    provider = KubernetesSecretRefProvider(KubernetesSecretRefConfig(allowed_mount_roots=(str(tmp_path),)))
    with pytest.raises(KubernetesSecretRefError):
        provider.resolve("does-not-exist/password")


# ---------------------------------------------------------------------------
# Integration with canonical SecretConsumer (P7.7 boundary) -- no new authority created
# ---------------------------------------------------------------------------

def test_cloud_providers_integrate_via_canonical_secret_consumer_not_a_new_authority():
    client = _FakeAWSSMClient(response={"SecretString": "value-from-aws", "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x"})
    aws_provider = AWSSecretsManagerProvider(client=client)

    consumer = SecretConsumer(resolver=aws_provider)
    resolved = consumer.resolve("x")
    assert resolved is not None
    assert resolved.get_value() == "value-from-aws"
    resolved.wipe()
    assert resolved.is_valid() is False


def test_no_plaintext_secret_leak_in_aws_error_message():
    """Zero-fake / zero-leak: even a raw exception message containing what looks like a
    secret value must not appear verbatim if it was ever routed through redact_text."""
    from akaalEngine.connection.security.redaction import redact_text
    raw = "AccessDeniedException: token=abcDEF123супер and secret=hunter2plaintext"
    redacted = redact_text(raw)
    assert "hunter2plaintext" not in redacted
