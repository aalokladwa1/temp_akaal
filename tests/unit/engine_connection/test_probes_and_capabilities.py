"""
Unit tests for akaalEngine.connection.probes
============================================
Verifies fail-closed capability resolution, permission probing, and health diagnostics.
"""

import pytest

from akaalEngine.connection.catalog.capability_resolver import CapabilityResolver
from akaalEngine.connection.models.capability import CapabilitySupportStatus
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.errors import CapabilityMismatchError
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.probes.capabilities import CapabilityProbe
from akaalEngine.connection.probes.connectivity import ConnectivityProbe
from akaalEngine.connection.probes.health import HealthProbe
from akaalEngine.connection.probes.permissions import PermissionProbe


def test_capability_resolver_fail_closed():
    resolver = CapabilityResolver()

    # SQLite supports BULK_READ and BULK_WRITE, but does NOT support CDC_LOG_CAPTURE
    all_ok, missing, statuses = resolver.evaluate_capabilities(
        "sqlite", ["BULK_READ", "BULK_WRITE", "CDC_LOG_CAPTURE"]
    )
    assert all_ok is False
    assert "CDC_LOG_CAPTURE" in missing
    assert statuses["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_purpose_satisfaction_validation():
    resolver = CapabilityResolver()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")

    # Bulk read should pass
    resolver.validate_purpose_satisfaction(spec, SessionPurpose.BULK_SOURCE_READ)

    # CDC capture on SQLite must fail closed
    with pytest.raises(CapabilityMismatchError):
        resolver.validate_purpose_satisfaction(spec, SessionPurpose.CDC_CAPTURE)


def test_connectivity_probe_sqlite():
    probe = ConnectivityProbe()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    result = probe.test_connectivity(spec)

    assert result.is_successful is True
    assert result.provider_id == "sqlite"
    assert result.total_handshake_ms >= 0.0
    assert result.server_version is not None


def test_permission_probe_sqlite():
    probe = PermissionProbe()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    snapshot = probe.probe_permissions(spec, SessionPurpose.SCHEMA_DDL)

    assert snapshot.can_write is True
    assert snapshot.can_ddl is True
    assert "SELECT" in snapshot.granted_privileges


def test_health_probe_sqlite():
    probe = HealthProbe()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    snapshot = probe.check_health(spec)

    assert snapshot.state.value == "HEALTHY"
    assert snapshot.rtt_ms >= 0.0
