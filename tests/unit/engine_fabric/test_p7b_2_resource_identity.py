"""
tests.unit.engine_fabric.test_p7b_2_resource_identity
========================================================
P7B.2 hostile tests -- cloud resource identity & discovery.

Proves: EXISTS != DISCOVERED != REACHABLE != AUTHORIZED != TRUSTED_FOR_EXECUTION;
wrong account/subscription/project/tenancy; malformed locator; permission denied;
throttling; provider unavailable; cross-tenant locator rejected at construction.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.resource_identity import (
    AWSResourceLocator,
    AzureResourceLocator,
    GCPResourceLocator,
    OCIResourceLocator,
    ResourceDiscoveryRecord,
    ResourceLocatorValidationError,
    ResourceProofLevel,
    DiscoveryDenied,
    DiscoveryThrottled,
    DiscoveryUnavailable,
    discover_aws_resource,
    discover_azure_resource,
    discover_gcp_resource,
    discover_oci_resource,
)


def test_malformed_arn_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(arn="not-an-arn", account_id="123456789012")


def test_arn_account_mismatch_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(
            arn="arn:aws:s3:::examplebucket".replace("s3:::", "s3:us-east-1:999999999999:"),
            account_id="123456789012",
        )


def test_malformed_azure_resource_id_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(resource_id="not-a-resource-id", subscription_id="11111111-1111-1111-1111-111111111111")


def test_azure_resource_id_subscription_mismatch_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(
            resource_id="/subscriptions/22222222-2222-2222-2222-222222222222/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
            subscription_id="11111111-1111-1111-1111-111111111111",
        )


def test_gcp_resource_name_project_mismatch_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        GCPResourceLocator(resource_name="projects/other-project/buckets/mybucket", project_id="my-project")


def test_malformed_ocid_rejected():
    with pytest.raises(ResourceLocatorValidationError):
        OCIResourceLocator(ocid="not-an-ocid", compartment_ocid="ocid1.compartment.oc1..aaaa")


def test_discovery_record_can_never_carry_authorized_or_trusted_proof():
    aws_locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    with pytest.raises(ResourceLocatorValidationError):
        ResourceDiscoveryRecord(locator=aws_locator, proof_level=ResourceProofLevel.AUTHORIZED)
    with pytest.raises(ResourceLocatorValidationError):
        ResourceDiscoveryRecord(locator=aws_locator, proof_level=ResourceProofLevel.TRUSTED_FOR_EXECUTION)

    # REACHABLE is the maximum discovery can legitimately claim.
    record = ResourceDiscoveryRecord(locator=aws_locator, proof_level=ResourceProofLevel.REACHABLE)
    assert record.at_least(ResourceProofLevel.DISCOVERED)
    assert not record.at_least(ResourceProofLevel.AUTHORIZED)


def test_stale_record_never_counts_as_proof():
    aws_locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    record = ResourceDiscoveryRecord(locator=aws_locator, proof_level=ResourceProofLevel.REACHABLE, stale=True)
    assert not record.at_least(ResourceProofLevel.EXISTS)


class _FakeSTSClient:
    def __init__(self, account: str, arn: str = "arn:aws:iam::123456789012:user/test", raise_exc: Exception = None):
        self.account = account
        self.arn = arn
        self.raise_exc = raise_exc

    def get_caller_identity(self):
        if self.raise_exc:
            raise self.raise_exc
        return {"Account": self.account, "Arn": self.arn}


def test_aws_discovery_wrong_account_fails_closed():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    wrong_account_client = _FakeSTSClient(account="999999999999")
    with pytest.raises(DiscoveryDenied):
        discover_aws_resource(locator, sts_client=wrong_account_client)


def test_aws_discovery_correct_account_reaches_reachable_not_higher():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    good_client = _FakeSTSClient(account="123456789012")
    outcome = discover_aws_resource(locator, sts_client=good_client)
    assert outcome.succeeded
    assert outcome.record.proof_level == ResourceProofLevel.REACHABLE


def test_aws_discovery_permission_denied_maps_to_discovery_denied():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    denying_client = _FakeSTSClient(account="123456789012", raise_exc=Exception("AccessDenied: user is not authorized"))
    with pytest.raises(DiscoveryDenied):
        discover_aws_resource(locator, sts_client=denying_client)


def test_aws_discovery_throttling_mapped_distinctly():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    throttling_client = _FakeSTSClient(account="123456789012", raise_exc=Exception("ThrottlingException: Rate exceeded"))
    with pytest.raises(DiscoveryThrottled):
        discover_aws_resource(locator, sts_client=throttling_client)


def test_aws_discovery_provider_unavailable_mapped_distinctly():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/mybucket", account_id="123456789012")
    down_client = _FakeSTSClient(account="123456789012", raise_exc=Exception("EndpointConnectionError: could not connect"))
    with pytest.raises(DiscoveryUnavailable):
        discover_aws_resource(locator, sts_client=down_client)


class _FakeAzureResourceClientNamespace:
    def __init__(self, resource=None, raise_exc: Exception = None):
        self._resource = resource
        self._raise_exc = raise_exc

    def get_by_id(self, resource_id, api_version):
        if self._raise_exc:
            raise self._raise_exc
        return self._resource


class _FakeAzureResourceClient:
    def __init__(self, resource=None, raise_exc: Exception = None):
        self.resources = _FakeAzureResourceClientNamespace(resource, raise_exc)


def test_azure_discovery_authorization_failed_maps_to_denied():
    locator = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    client = _FakeAzureResourceClient(raise_exc=Exception("AuthorizationFailed: does not have authorization"))
    with pytest.raises(DiscoveryDenied):
        discover_azure_resource(locator, resource_client=client)


def test_azure_discovery_success_reaches_reachable():
    locator = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )

    class _Res:
        type = "Microsoft.Storage/storageAccounts"
        properties = {"provisioningState": "Succeeded"}

    client = _FakeAzureResourceClient(resource=_Res())
    outcome = discover_azure_resource(locator, resource_client=client)
    assert outcome.record.proof_level == ResourceProofLevel.REACHABLE


class _FakeGCPClient:
    def __init__(self, resource=None, raise_exc: Exception = None):
        self._resource = resource
        self._raise_exc = raise_exc

    def get(self, name):
        if self._raise_exc:
            raise self._raise_exc
        return self._resource


def test_gcp_discovery_permission_denied_maps_to_denied():
    locator = GCPResourceLocator(resource_name="projects/my-project/buckets/mybucket", project_id="my-project")
    client = _FakeGCPClient(raise_exc=Exception("PermissionDenied: 403 caller does not have permission"))
    with pytest.raises(DiscoveryDenied):
        discover_gcp_resource(locator, client=client)


class _FakeOCIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class _FakeOCIClient:
    def __init__(self, resource=None, raise_exc: Exception = None):
        self._resource = resource
        self._raise_exc = raise_exc

    def get_resource(self, ocid):
        if self._raise_exc:
            raise self._raise_exc
        return self._resource


def test_oci_discovery_not_found_maps_to_unavailable():
    locator = OCIResourceLocator(ocid="ocid1.bucket.oc1.iad.aaaa", compartment_ocid="ocid1.compartment.oc1..bbbb")
    client = _FakeOCIClient(raise_exc=_FakeOCIError(404, "resource not found"))
    with pytest.raises(DiscoveryUnavailable):
        discover_oci_resource(locator, client=client)


def test_oci_discovery_throttled_maps_distinctly():
    locator = OCIResourceLocator(ocid="ocid1.bucket.oc1.iad.aaaa", compartment_ocid="ocid1.compartment.oc1..bbbb")
    client = _FakeOCIClient(raise_exc=_FakeOCIError(429, "too many requests"))
    with pytest.raises(DiscoveryThrottled):
        discover_oci_resource(locator, client=client)
