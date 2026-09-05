"""
tests.unit.engine_connection.test_couchbase_provider
========================================================
Dedicated hostile/unit tests for the Couchbase provider strategy (P7A Campaign B).

Covers negative capability truth (FOREIGN_KEYS/CDC_LOG_CAPTURE not fabricated),
multi-node-cluster topology truth, and Couchbase-specific error normalization
(CAS conflicts, document-not-found, timeouts).
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.nosql.couchbase import CouchbaseProviderStrategy


def test_static_manifest_does_not_fabricate_foreign_keys_or_cdc():
    strat = CouchbaseProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["FOREIGN_KEYS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["SCHEMA_DISCOVERY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = CouchbaseProviderStrategy()
    assert strat.PROVIDER_ID == "couchbase"
    manifest = strat.get_static_manifest()
    assert manifest.family == "nosql"


def test_validate_configuration_requires_host():
    strat = CouchbaseProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="couchbase", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="couchbase", host="couchbase.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = CouchbaseProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="couchbase", host="couchbase.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_probe_permissions_reports_no_privileges_without_connection():
    strat = CouchbaseProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="couchbase", host="couchbase.internal")
    snapshot = strat.probe_permissions(None, spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.granted_privileges == []


def test_attest_physical_identity_reports_multi_node_cluster_topology():
    strat = CouchbaseProviderStrategy()
    spec = EndpointSpec(provider_id="couchbase", host="couchbase.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="couchbase.internal", effective_port=11210, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "MULTI_NODE_CLUSTER"


def test_normalize_error_cas_conflict_is_retryable():
    strat = CouchbaseProviderStrategy()

    class CasMismatchException(Exception):
        pass

    failure = strat.normalize_error(CasMismatchException("CAS mismatch detected"))
    assert failure.error_code == "COUCHBASE_CAS_CONFLICT"
    assert failure.retryable is True


def test_normalize_error_document_not_found_not_retryable():
    strat = CouchbaseProviderStrategy()

    class DocumentNotFoundException(Exception):
        pass

    failure = strat.normalize_error(DocumentNotFoundException("document not found"))
    assert failure.error_code == "COUCHBASE_DOCUMENT_NOT_FOUND"
    assert failure.retryable is False


def test_normalize_error_auth_failure():
    strat = CouchbaseProviderStrategy()

    class AuthenticationException(Exception):
        pass

    failure = strat.normalize_error(AuthenticationException("Authentication failed"))
    assert failure.error_code == "COUCHBASE_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_timeout_is_retryable():
    strat = CouchbaseProviderStrategy()

    class AmbiguousTimeoutException(Exception):
        pass

    failure = strat.normalize_error(AmbiguousTimeoutException("operation timeout"))
    assert failure.error_code == "COUCHBASE_TIMEOUT"
    assert failure.retryable is True


def test_is_dependency_available_truthfully_reports_missing_sdk():
    strat = CouchbaseProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is False
    assert "couchbase" in msg


def test_connect_raises_dependency_missing_when_sdk_unavailable():
    strat = CouchbaseProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="couchbase", host="couchbase.internal")
    route = ResolvedRoute(effective_host="couchbase.internal", effective_port=11210, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = CouchbaseProviderStrategy()
    assert strat.validate(None) is False
