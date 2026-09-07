"""
tests.unit.engine_connection.test_oci_object_storage_provider
================================================================
Dedicated hostile/unit tests for the OCI Object Storage provider strategy
(P7B Group 1, §8: OCI Object Storage first-class alongside S3/GCS/Azure Blob).

Covers negative capability truth (S3_SELECT genuinely unsupported, not borrowed from
S3's manifest), fail-closed dependency-missing path, region-required validation,
OCI-specific error normalization (401/403/404/429/5xx), and permission-probe truth.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec, RouteType
from akaalEngine.connection.models.errors import ConfigurationError, DependencyMissingError
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.storage.oci_object_storage import OCIObjectStorageProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute


def _spec(**options) -> EndpointSpec:
    return EndpointSpec(provider_id="oci_object_storage", region=options.pop("region", "us-ashburn-1"), options=options)


def test_provider_id_and_family():
    strat = OCIObjectStorageProviderStrategy()
    assert strat.PROVIDER_ID == "oci_object_storage"
    manifest = strat.get_static_manifest()
    assert manifest.family == "storage"
    assert manifest.vendor_name == "Oracle Cloud Infrastructure"


def test_static_manifest_does_not_fabricate_s3_select():
    strat = OCIObjectStorageProviderStrategy()
    manifest = strat.get_static_manifest()

    # OCI Object Storage has no server-side SQL-over-object equivalent to S3 Select --
    # must not inherit S3's SUPPORTED claim.
    assert manifest.capabilities["S3_SELECT"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["BUCKET_DISCOVERY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["SERVER_SIDE_COPY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_dependency_missing_fails_closed_on_connect():
    strat = OCIObjectStorageProviderStrategy()
    avail, _ = strat.is_dependency_available()
    if avail:
        pytest.skip("oci SDK is installed in this environment; dependency-missing path not exercisable.")

    spec = _spec(namespace="mynamespace", bucket="mybucket")
    route = ResolvedRoute(effective_host="objectstorage.us-ashburn-1.oraclecloud.com", effective_port=443)
    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, credentials={})


def test_validate_configuration_rejects_empty_namespace():
    strat = OCIObjectStorageProviderStrategy()
    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="oci_object_storage", options={"namespace": "  "}))

    # A missing namespace (None) is not itself rejected at validate_configuration time --
    # matches the established S3/DynamoDB pattern of deferring hard requirements to connect().
    strat.validate_configuration(EndpointSpec(provider_id="oci_object_storage", options={}))


def test_connect_fails_closed_without_region_when_dependency_available():
    strat = OCIObjectStorageProviderStrategy()
    avail, _ = strat.is_dependency_available()
    if not avail:
        pytest.skip("oci SDK not installed; region-required path requires the dependency to be present.")

    spec = EndpointSpec(provider_id="oci_object_storage", options={"namespace": "ns"})
    route = ResolvedRoute(effective_host="objectstorage.oraclecloud.com", effective_port=443)
    with pytest.raises(ConfigurationError):
        strat.connect(spec, route, credentials={})


def test_validate_returns_false_for_none_connection():
    strat = OCIObjectStorageProviderStrategy()
    assert strat.validate(None) is False


def test_validate_returns_false_when_get_namespace_raises():
    strat = OCIObjectStorageProviderStrategy()

    class _FailingConn:
        def get_namespace(self):
            raise RuntimeError("simulated OCI outage")

    assert strat.validate(_FailingConn()) is False


def test_probe_permissions_never_claims_ddl_or_cdc_or_admin():
    strat = OCIObjectStorageProviderStrategy()
    spec = _spec(namespace="ns", bucket="b")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_ddl is False
    assert snapshot.can_cdc is False
    assert snapshot.is_admin is False


def test_attest_physical_identity_reports_object_store_topology_and_region():
    strat = OCIObjectStorageProviderStrategy()
    spec = _spec(namespace="ns", bucket="mybucket", region="eu-frankfurt-1")
    route = ResolvedRoute(effective_host="objectstorage.eu-frankfurt-1.oraclecloud.com", effective_port=443, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(object(), spec, route)
    assert identity.topology_role == "OBJECT_STORE"
    assert identity.cloud_region == "eu-frankfurt-1"
    assert identity.catalog_or_database == "mybucket"


@pytest.mark.parametrize(
    "status,code,expected_error_code,expected_retryable",
    [
        (401, "NotAuthenticated", "OCI_OBJECT_STORAGE_AUTH_FAILED", False),
        (403, "NotAuthorizedOrNotFound", "OCI_OBJECT_STORAGE_PERMISSION_DENIED", False),
        (404, "BucketNotFound", "OCI_OBJECT_STORAGE_BUCKET_NOT_FOUND", False),
        (429, "TooManyRequests", "OCI_OBJECT_STORAGE_THROTTLED", True),
        (503, "ServiceUnavailable", "OCI_OBJECT_STORAGE_SERVICE_UNAVAILABLE", True),
    ],
)
def test_normalize_error_maps_oci_service_errors_truthfully(status, code, expected_error_code, expected_retryable):
    strat = OCIObjectStorageProviderStrategy()

    class _FakeOCIServiceError(Exception):
        def __init__(self, status, code, message):
            super().__init__(message)
            self.status = status
            self.code = code

    exc = _FakeOCIServiceError(status, code, f"simulated {code}")
    failure = strat.normalize_error(exc)
    assert failure.error_code == expected_error_code
    assert failure.retryable == expected_retryable
    assert failure.provider_id == "oci_object_storage"


def test_normalize_error_unclassified_defaults_to_non_retryable_internal_error():
    strat = OCIObjectStorageProviderStrategy()
    failure = strat.normalize_error(RuntimeError("totally unexpected condition"))
    assert failure.error_code == "OCI_OBJECT_STORAGE_ERROR"
    assert failure.retryable is False


def test_normalize_error_redacts_secret_material():
    strat = OCIObjectStorageProviderStrategy()
    exc = RuntimeError("auth failed for user token=SUPERSECRETPRIVATEKEYDATA")
    failure = strat.normalize_error(exc)
    assert "SUPERSECRETPRIVATEKEYDATA" not in failure.message


def test_extensions_authority_adopts_oci_object_storage_provider():
    from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog

    assert default_provider_catalog.is_provider_registered("oci_object_storage")
    manifest = default_provider_catalog.describe_provider("oci_object_storage")
    assert manifest.family == "storage"


def test_discovery_strategy_registered_and_reports_correct_provider_id():
    from akaalEngine.discovery.strategies import ALL_DISCOVERY_STRATEGIES

    matches = [s for s in ALL_DISCOVERY_STRATEGIES if s().provider_id == "oci_object_storage"]
    assert len(matches) == 1


def test_discovery_reports_no_fabricated_cdc_readiness_without_connection():
    from akaalEngine.discovery.strategies.storage.oci_object_storage import OCIObjectStorageDiscoveryStrategy
    from akaalEngine.discovery.models.cdc import CDCMechanism

    strat = OCIObjectStorageDiscoveryStrategy()
    spec = _spec(namespace="ns", bucket="b")
    snap = strat.discover_cdc_prerequisites(None, spec, context=None)
    assert snap.is_cdc_ready is False
    assert snap.mechanism == CDCMechanism.UNSUPPORTED


def test_discovery_namespace_inventory_falls_back_to_configured_bucket_without_connection():
    from akaalEngine.discovery.strategies.storage.oci_object_storage import OCIObjectStorageDiscoveryStrategy

    strat = OCIObjectStorageDiscoveryStrategy()
    spec = _spec(namespace="ns", bucket="mybucket")
    inv = strat.discover_namespaces(None, spec, context=None)
    assert inv.buckets == ("mybucket",)
