"""
Unit tests for akaalEngine.connection.api.authority
===================================================
Verifies the Single Canonical ConnectionAuthority façade.
Ensures zero leakage of native handles, secrets, or mutable pool internals across public DTOs.
"""

import pytest

from akaalEngine.connection.api.authority import ConnectionAuthority
from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
)
from akaalEngine.connection.models.session import (
    IsolationLevel,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.security.secret_consumer import default_secret_consumer, InMemorySecretResolver


def test_connection_authority_singleton_and_list():
    authority = ConnectionAuthority.get_instance()
    providers = authority.list_providers()
    assert "sqlite" in providers
    assert "postgresql" in providers
    assert "mysql" in providers
    assert "oracle" in providers
    assert len(providers) >= 28


def test_connection_authority_describe_provider():
    authority = ConnectionAuthority.get_instance()
    manifest = authority.describe_provider("postgresql")
    assert manifest.provider_id == "postgresql"
    assert manifest.vendor_name == "PostgreSQL Global Development Group"
    assert manifest.is_capability_supported("BINARY_COPY") is True


def test_connection_authority_public_probe_sanitization():
    default_secret_consumer.register_resolver(InMemorySecretResolver({"vault://secret/token": "SUPER_SECRET_VALUE_XYZ"}))
    authority = ConnectionAuthority.get_instance()
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=":memory:",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="admin",
            secret_ref="vault://secret/token",
        ),
    )

    # Connectivity test
    test_result = authority.test_connectivity(spec)
    assert test_result.is_successful is True
    res_dict = test_result.to_dict()
    assert "token" not in str(res_dict)

    # Identity attestation
    identity = authority.attest_endpoint_identity(spec)
    assert identity.server_version is not None
    assert identity.provider_id == "sqlite"
    id_dict = identity.to_dict()
    assert "token" not in str(id_dict)

    # Health snapshot
    health = authority.get_health(spec)
    assert health.state.value == "HEALTHY"
    health_dict = health.to_dict()
    assert "token" not in str(health_dict)


def test_connection_authority_session_lease_lifecycle():
    authority = ConnectionAuthority.get_instance()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.SOURCE)
    req = SessionRequest(
        purpose=SessionPurpose.BULK_SOURCE_READ,
        endpoint_spec=spec,
        isolation_level=IsolationLevel.AUTOCOMMIT,
        borrower_id="engine-task-01",
    )

    # Acquire lease
    lease = authority.acquire_session_lease(req, borrower_id="engine-task-01")
    assert lease.is_valid() is True
    assert lease.borrower_id == "engine-task-01"

    # Validate lease
    assert authority.validate_lease(lease) is True

    # Renew lease
    renewed = authority.renew_lease(lease, extension_seconds=600.0)
    assert renewed.is_valid() is True

    # Check pool snapshot
    pool_snap = authority.get_pool_snapshot(spec)
    assert pool_snap is not None
    assert pool_snap.active_count == 1

    # Release lease
    released = authority.release_session_lease(lease)
    assert released is True

    # Pool reflects released idle connection
    snap_after = authority.get_pool_snapshot(spec)
    assert snap_after.active_count == 0
    assert snap_after.idle_count == 1

    # Cleanup
    authority.invalidate_endpoint(spec)
