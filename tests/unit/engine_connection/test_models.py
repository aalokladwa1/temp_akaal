"""
Unit tests for akaalEngine.connection.models
===========================================
Verifies immutability, serialization, and contract invariants.
"""

import pytest
from dataclasses import FrozenInstanceError

from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    RouteSpec,
    RouteType,
    TLSBinding,
    TLSMode,
)
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    ConnectionEngineException,
)
from akaalEngine.connection.models.identity import (
    DriftReport,
    DriftSeverity,
    DriftType,
    EndpointBindingFingerprint,
    PhysicalEndpointIdentity,
)
from akaalEngine.connection.models.capability import (
    CapabilityDescriptor,
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.session import (
    InternalSessionHandle,
    IsolationLevel,
    SessionLease,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.models.health import (
    ConnectionHealthSnapshot,
    ConnectionPressureSnapshot,
    ConnectionTestResult,
    HealthState,
    PoolSnapshot,
)


def test_endpoint_spec_immutability():
    spec = EndpointSpec(
        provider_id="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb",
        role=EndpointRole.SOURCE,
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        spec.host = "otherhost"  # type: ignore


def test_auth_spec_immutability():
    auth = AuthenticationSpec(
        auth_type=AuthenticationType.PASSWORD,
        username="postgres",
        secret_ref="vault://pg/pass",
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        auth.username = "root"  # type: ignore


def test_session_purpose_properties():
    assert SessionPurpose.DISCOVERY.is_read_only_by_default is True
    assert SessionPurpose.VALIDATION_READ.is_read_only_by_default is True
    assert SessionPurpose.BULK_TARGET_WRITE.is_read_only_by_default is False
    assert SessionPurpose.SCHEMA_DDL.requires_ddl_privilege is True
    assert SessionPurpose.CDC_CAPTURE.is_long_lived is True


def test_connection_failure_serialization():
    fail = ConnectionFailure(
        error_code="TEST_ERR",
        category=FailureCategory.INVALID_CONFIGURATION,
        message="Invalid port",
        retryable=False,
        provider_id="postgresql",
    )
    d = fail.to_dict()
    assert d["error_code"] == "TEST_ERR"
    assert d["category"] == "INVALID_CONFIGURATION"
    assert d["retryable"] is False


def test_manifest_fail_closed_logic():
    manifest = StaticCapabilityManifest(
        provider_id="test_db",
        provider_version="1.0.0",
        family="relational",
        vendor_name="TestCorp",
        capabilities={
            "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
        },
    )
    assert manifest.is_capability_supported("SCHEMA_DISCOVERY") is True
    assert manifest.is_capability_supported("CDC_LOG_CAPTURE") is False
    # Unknown capability must fail closed (return False)
    assert manifest.is_capability_supported("NON_EXISTENT_FEATURE") is False
    assert manifest.get_status("NON_EXISTENT_FEATURE") == CapabilitySupportStatus.UNKNOWN
