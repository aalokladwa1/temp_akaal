"""
tests.unit.engine_connection.test_dynamodb_provider
=======================================================
Dedicated hostile/unit tests for the AWS DynamoDB provider strategy (P7A Campaign B).

Covers negative capability truth (FOREIGN_KEYS/CDC_LOG_CAPTURE not fabricated),
fail-closed per-table DynamoDB Streams probing, managed-service topology truth, and
AWS ClientError-shaped error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.nosql.dynamodb import DynamoDBProviderStrategy


def test_static_manifest_does_not_fabricate_foreign_keys_or_cdc():
    strat = DynamoDBProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["FOREIGN_KEYS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["PARTITION_AWARENESS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = DynamoDBProviderStrategy()
    assert strat.PROVIDER_ID == "dynamodb"
    manifest = strat.get_static_manifest()
    assert manifest.family == "nosql"


def test_probe_capabilities_fails_closed_without_table_name():
    strat = DynamoDBProviderStrategy()

    class FakeConnection:
        def describe_table(self, TableName):
            raise AssertionError("should not be called without a table_name in scope")

    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1")
    snapshot = strat.probe_capabilities(FakeConnection(), spec)
    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_capabilities_elevates_only_on_truthful_stream_enabled():
    strat = DynamoDBProviderStrategy()

    class FakeConnection:
        def __init__(self, enabled: bool):
            self._enabled = enabled

        def describe_table(self, TableName):
            return {"Table": {"StreamSpecification": {"StreamEnabled": self._enabled}}}

    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1", options={"table_name": "orders"})

    enabled_snapshot = strat.probe_capabilities(FakeConnection(True), spec)
    assert enabled_snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.SUPPORTED

    disabled_snapshot = strat.probe_capabilities(FakeConnection(False), spec)
    assert disabled_snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_capabilities_fails_closed_on_describe_table_exception():
    strat = DynamoDBProviderStrategy()

    class FakeConnection:
        def describe_table(self, TableName):
            raise RuntimeError("AccessDeniedException")

    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1", options={"table_name": "orders"})
    snapshot = strat.probe_capabilities(FakeConnection(), spec)
    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_permissions_never_claims_cdc_capability():
    strat = DynamoDBProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1")
    snapshot = strat.probe_permissions(None, spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False
    assert snapshot.granted_privileges == []


def test_attest_physical_identity_reports_managed_partitioned_store():
    strat = DynamoDBProviderStrategy()
    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="dynamodb.us-east-1.amazonaws.com", effective_port=443, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "MANAGED_PARTITIONED_STORE"


class _ClientErrorLike(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.response = {"Error": {"Code": code, "Message": message}}


def test_normalize_error_resource_not_found():
    strat = DynamoDBProviderStrategy()
    failure = strat.normalize_error(_ClientErrorLike("ResourceNotFoundException", "Table not found"))
    assert failure.error_code == "DYNAMODB_TABLE_NOT_FOUND"
    assert failure.retryable is False


def test_normalize_error_throughput_exceeded_is_retryable():
    strat = DynamoDBProviderStrategy()
    failure = strat.normalize_error(_ClientErrorLike("ProvisionedThroughputExceededException", "Rate exceeded"))
    assert failure.error_code == "DYNAMODB_THROUGHPUT_EXCEEDED"
    assert failure.retryable is True


def test_normalize_error_access_denied():
    strat = DynamoDBProviderStrategy()
    failure = strat.normalize_error(_ClientErrorLike("AccessDeniedException", "not authorized"))
    assert failure.error_code == "DYNAMODB_PERMISSION_DENIED"
    assert failure.retryable is False


def test_normalize_error_conditional_check_failed_not_retryable():
    strat = DynamoDBProviderStrategy()
    failure = strat.normalize_error(_ClientErrorLike("ConditionalCheckFailedException", "condition failed"))
    assert failure.error_code == "DYNAMODB_CONDITIONAL_CHECK_FAILED"
    assert failure.retryable is False


def test_is_dependency_available_truthfully_reports_missing_boto3():
    strat = DynamoDBProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is False
    assert "boto3" in msg


def test_connect_raises_dependency_missing_when_boto3_unavailable():
    strat = DynamoDBProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="dynamodb", region="us-east-1")
    route = ResolvedRoute(effective_host="dynamodb.us-east-1.amazonaws.com", effective_port=443, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})
