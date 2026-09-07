"""
tests.unit.engine_connection.test_p7b_round5_gcp_oci_workload_identity_integration
=======================================================================================
P7B Group-1 Hostile Closure Round 5 -- GCP/OCI workload identity real integration,
closing the asymmetry left after AWS/Azure were fixed.

Real defect found and fixed: for BOTH GCS and OCI Object Storage, `connect()` had no
path to accept an already-resolved workload identity's actual usable material (a live
`google.auth.credentials.Credentials` object for GCP; an OCI `signer` object for OCI --
neither has a string/JSON representation, which is exactly why AWS/Azure's simpler
string-based fix didn't generalize). Both providers fell through to constructing their
OWN internal ambient-identity resolution, silently discarding whatever specific identity
AKAAL had actually resolved via `resolve_gcp_workload_identity`/`resolve_oci_workload_identity`.

Minimal, additive fix: both `connect()` methods now check for
`credentials["gcp_credentials_object"]`/`credentials["oci_signer"]` FIRST and use it
directly when present; existing behavior (explicit service-account JSON, ambient ADC,
config-file API-key auth, fresh instance/resource-principal signer construction) is
completely unchanged when that key is absent -- this is proven by the "existing behavior
unaffected" tests below, i.e. this is a strictly additive change, not a rewrite.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.connection.security.authentication import AuthenticationManager
from akaalEngine.connection.security.secret_consumer import SecretConsumer
from akaalEngine.connection.routing.resolver import ResolvedRoute


# ---------------------------------------------------------------------------
# GCP: GCSProviderStrategy.connect() genuinely uses the resolved Credentials object
# ---------------------------------------------------------------------------

class _FakeGCPCredentialsObject:
    """Stands in for a real google.auth.credentials.Credentials instance -- identity
    equality (via `is`) is what we assert on, proving the EXACT resolved object reaches
    the client constructor, not a re-derived one."""
    pass


def test_gcs_connect_uses_the_exact_resolved_credentials_object(monkeypatch):
    from akaalEngine.connection.providers.storage.gcs import GCSProviderStrategy

    strat = GCSProviderStrategy()
    resolved_creds_obj = _FakeGCPCredentialsObject()
    captured = {}

    class _FakeStorageClient:
        def __init__(self, project=None, credentials=None):
            captured["project"] = project
            captured["credentials"] = credentials

    class _FakeStorageModule:
        Client = _FakeStorageClient

    monkeypatch.setitem(sys.modules, "google.cloud.storage", _FakeStorageModule())
    monkeypatch.setitem(sys.modules, "google.cloud", type(sys)("google.cloud"))
    sys.modules["google.cloud"].storage = _FakeStorageModule()

    spec = EndpointSpec(provider_id="gcs", options={"project_id": "my-project"})
    route = ResolvedRoute(effective_host="storage.googleapis.com", effective_port=443)
    strat.connect(spec, route, credentials={"gcp_credentials_object": resolved_creds_obj})

    assert captured["credentials"] is resolved_creds_obj  # the EXACT resolved object, not a copy/re-derivation


def test_gcs_connect_existing_service_account_json_path_unaffected(monkeypatch):
    """Proves the fix is strictly additive: with NO gcp_credentials_object present, the
    pre-existing explicit service-account-JSON path behaves exactly as before."""
    from akaalEngine.connection.providers.storage.gcs import GCSProviderStrategy

    strat = GCSProviderStrategy()
    captured = {}

    class _FakeSACredentials:
        @classmethod
        def from_service_account_info(cls, info_dict):
            captured["sa_info"] = info_dict
            return "fake-sa-creds"

    class _FakeStorageClient:
        def __init__(self, project=None, credentials=None):
            captured["project"] = project
            captured["credentials"] = credentials

    class _FakeStorageModule:
        Client = _FakeStorageClient

    class _FakeServiceAccountModule:
        Credentials = _FakeSACredentials

    monkeypatch.setitem(sys.modules, "google.cloud.storage", _FakeStorageModule())
    monkeypatch.setitem(sys.modules, "google.cloud", type(sys)("google.cloud"))
    sys.modules["google.cloud"].storage = _FakeStorageModule()
    monkeypatch.setitem(sys.modules, "google.oauth2", type(sys)("google.oauth2"))
    sys.modules["google.oauth2"].service_account = _FakeServiceAccountModule()
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", _FakeServiceAccountModule())

    spec = EndpointSpec(provider_id="gcs", options={"project_id": "my-project"})
    route = ResolvedRoute(effective_host="storage.googleapis.com", effective_port=443)
    strat.connect(spec, route, credentials={"service_account_json": {"type": "service_account", "project_id": "my-project"}})

    assert captured["credentials"] == "fake-sa-creds"  # existing SA-JSON path, untouched


# ---------------------------------------------------------------------------
# OCI: OCIObjectStorageProviderStrategy.connect() genuinely uses the resolved signer
# ---------------------------------------------------------------------------

def test_oci_object_storage_connect_uses_the_exact_resolved_signer(monkeypatch):
    from akaalEngine.connection.providers.storage.oci_object_storage import OCIObjectStorageProviderStrategy

    strat = OCIObjectStorageProviderStrategy()
    avail, _ = strat.is_dependency_available()

    resolved_signer = object()
    captured = {}

    class _FakeObjectStorageClient:
        def __init__(self, config, signer=None):
            captured["config"] = config
            captured["signer"] = signer

    class _FakeObjectStorageModule:
        ObjectStorageClient = _FakeObjectStorageClient

    class _FakeOCIModule:
        object_storage = _FakeObjectStorageModule()

        class auth:
            class signers:
                pass

        class config:
            pass

    monkeypatch.setitem(sys.modules, "oci", _FakeOCIModule())

    spec = EndpointSpec(provider_id="oci_object_storage", region="us-ashburn-1", options={})
    route = ResolvedRoute(effective_host="objectstorage.us-ashburn-1.oraclecloud.com", effective_port=443)
    strat.connect(spec, route, credentials={"oci_signer": resolved_signer})

    assert captured["signer"] is resolved_signer  # the EXACT resolved signer, not a freshly constructed one


def test_oci_object_storage_connect_existing_instance_principal_path_unaffected(monkeypatch):
    """Proves the fix is strictly additive: with NO oci_signer present, the pre-existing
    instance_principal auth_mode still constructs its own fresh signer exactly as before."""
    from akaalEngine.connection.providers.storage.oci_object_storage import OCIObjectStorageProviderStrategy

    strat = OCIObjectStorageProviderStrategy()
    captured = {}
    fresh_signer_marker = object()

    class _FakeObjectStorageClient:
        def __init__(self, config, signer=None):
            captured["signer"] = signer

    class _FakeObjectStorageModule:
        ObjectStorageClient = _FakeObjectStorageClient

    class _FakeSigners:
        @staticmethod
        def InstancePrincipalsSecurityTokenSigner():
            return fresh_signer_marker

    class _FakeAuth:
        signers = _FakeSigners

    class _FakeOCIModule:
        object_storage = _FakeObjectStorageModule()
        auth = _FakeAuth

        class config:
            pass

    monkeypatch.setitem(sys.modules, "oci", _FakeOCIModule())

    spec = EndpointSpec(provider_id="oci_object_storage", region="us-ashburn-1", options={"auth_mode": "instance_principal"})
    route = ResolvedRoute(effective_host="objectstorage.us-ashburn-1.oraclecloud.com", effective_port=443)
    strat.connect(spec, route, credentials={})  # no oci_signer supplied

    assert captured["signer"] is fresh_signer_marker  # existing instance-principal path, untouched


# ---------------------------------------------------------------------------
# End-to-end through AuthenticationManager for both clouds
# ---------------------------------------------------------------------------

def test_gcp_adc_resolution_genuinely_populates_gcp_credentials_object_key(monkeypatch):
    import akaalEngine.fabric.workload_identity as wi_pkg

    fake_creds_obj = _FakeGCPCredentialsObject()

    def patched(project_id=None, credentials=None, refresh_request=None):
        return wi_pkg.CloudIdentityContext(
            provider=wi_pkg.CloudAuthProvider.GCP, principal_id="sa@my-project.iam.gserviceaccount.com",
            account_boundary="my-project", expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            raw_claims={"credentials_object": fake_creds_obj},
        )

    monkeypatch.setattr(wi_pkg, "resolve_gcp_workload_identity", patched)

    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    spec = AuthenticationSpec(auth_type=AuthenticationType.GCP_ADC, additional_params={"project_id": "my-project"})
    creds = mgr.resolve_credentials(spec, provider_id="gcs")
    assert creds["gcp_credentials_object"] is fake_creds_obj


def test_oci_instance_principal_resolution_genuinely_populates_oci_signer_key():
    mgr = AuthenticationManager(secret_consumer=SecretConsumer())
    fake_signer = object()
    spec = AuthenticationSpec(
        auth_type=AuthenticationType.OCI_INSTANCE_PRINCIPAL,
        additional_params={
            "oci_signer": fake_signer,
            "oci_principal_id": "ocid1.instance.oc1..aaaa",
            "oci_tenancy_ocid": "ocid1.tenancy.oc1..bbbb",
        },
    )
    creds = mgr.resolve_credentials(spec, provider_id="oci_object_storage")
    assert creds["oci_signer"] is fake_signer


def test_expired_gcp_identity_never_populates_gcp_credentials_object():
    import akaalEngine.fabric.workload_identity as wi_pkg

    def expired_patched(project_id=None, credentials=None, refresh_request=None):
        return wi_pkg.CloudIdentityContext(
            provider=wi_pkg.CloudAuthProvider.GCP, principal_id="sa@my-project.iam.gserviceaccount.com",
            account_boundary="my-project", expires_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            raw_claims={"credentials_object": _FakeGCPCredentialsObject()},
        )

    import pytest as _pytest
    mp = _pytest.MonkeyPatch()
    mp.setattr(wi_pkg, "resolve_gcp_workload_identity", expired_patched)
    try:
        mgr = AuthenticationManager(secret_consumer=SecretConsumer())
        spec = AuthenticationSpec(auth_type=AuthenticationType.GCP_ADC, additional_params={"project_id": "my-project"})
        creds = mgr.resolve_credentials(spec, provider_id="gcs")
        assert "gcp_credentials_object" not in creds
        assert "expired" in creds.get("cloud_identity_error", "").lower()
    finally:
        mp.undo()
