"""
Unit tests for akaalEngine.connection.identity
==============================================
Verifies deterministic secret-free fingerprinting, identity attestation, and drift detection.
"""

from akaalEngine.connection.identity.attestation import IdentityAttestor
from akaalEngine.connection.identity.drift import DriftDetector
from akaalEngine.connection.identity.fingerprint import (
    canonicalize_endpoint_spec,
    compute_endpoint_fingerprint,
)
from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    RouteSpec,
    RouteType,
)
from akaalEngine.connection.models.identity import (
    DriftSeverity,
    DriftType,
    PhysicalEndpointIdentity,
)


def test_deterministic_fingerprint():
    spec1 = EndpointSpec(
        provider_id="postgresql",
        host="db.example.com",
        port=5432,
        database_name="appdb",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="appuser",
            secret_ref="vault://secret/v1",
            secret_version="1",
        ),
    )

    spec2 = EndpointSpec(
        provider_id="postgresql",
        host="db.example.com",
        port=5432,
        database_name="appdb",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="appuser",
            secret_ref="vault://secret/v1",
            secret_version="1",
        ),
    )

    fp1 = compute_endpoint_fingerprint(spec1)
    fp2 = compute_endpoint_fingerprint(spec2)

    assert fp1.fingerprint_sha256 == fp2.fingerprint_sha256
    assert len(fp1.fingerprint_sha256) == 64


def test_fingerprint_excludes_secret_material():
    spec = EndpointSpec(
        provider_id="mysql",
        host="mysql.internal",
        port=3306,
        options={"password": "raw_injected_password_123"},
    )
    fp = compute_endpoint_fingerprint(spec)
    assert "raw_injected_password_123" not in fp.canonical_payload_json


def test_drift_detector_ip_mutation():
    baseline = PhysicalEndpointIdentity(
        provider_id="postgresql",
        provider_version="1.0.0",
        role=EndpointRole.SOURCE,
        resolved_host="db.example.com",
        resolved_ip="10.0.0.1",
        server_version="PostgreSQL 15.2",
        topology_role="PRIMARY",
    )

    current = PhysicalEndpointIdentity(
        provider_id="postgresql",
        provider_version="1.0.0",
        role=EndpointRole.SOURCE,
        resolved_host="db.example.com",
        resolved_ip="10.0.0.2",
        server_version="PostgreSQL 15.2",
        topology_role="PRIMARY",
    )

    report = DriftDetector.compare_identities(baseline, current)
    assert report.has_drift is True
    assert report.drift_type == DriftType.IP_MUTATION
    assert "resolved_ip" in report.drifted_fields


def test_drift_detector_topology_failover():
    baseline = PhysicalEndpointIdentity(
        provider_id="postgresql",
        provider_version="1.0.0",
        role=EndpointRole.SOURCE,
        resolved_host="db.example.com",
        resolved_ip="10.0.0.1",
        server_version="PostgreSQL 15.2",
        topology_role="PRIMARY",
    )

    current = PhysicalEndpointIdentity(
        provider_id="postgresql",
        provider_version="1.0.0",
        role=EndpointRole.SOURCE,
        resolved_host="db.example.com",
        resolved_ip="10.0.0.1",
        server_version="PostgreSQL 15.2",
        topology_role="REPLICA",
    )

    report = DriftDetector.compare_identities(baseline, current)
    assert report.has_drift is True
    assert report.drift_type == DriftType.ROLE_TOPOLOGY_CHANGE
    assert report.severity == DriftSeverity.INVALIDATING_ERROR
    assert report.requires_pool_invalidation is True
