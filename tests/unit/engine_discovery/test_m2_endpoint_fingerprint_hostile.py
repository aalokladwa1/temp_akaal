"""
tests/unit/engine_discovery/test_m2_endpoint_fingerprint_hostile.py
==================================================================
Hostile verification of Endpoint Fingerprint Fail-Closed and Determinism Invariants.
Proves that fingerprints are canonical, deterministic, non-secret-leaking,
and do not embed arbitrary process memory addresses (0x...).
"""

import pytest
from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    TLSBinding,
    TLSMode,
)
from akaalEngine.discovery.authority import compute_endpoint_fingerprint, canonicalize_for_fingerprint


class ArbitraryMockConnection:
    """Mock connection object without __str__ override to test memory-address immunity."""
    def __init__(self, name="mock_rfc"):
        self.name = name


def test_01_same_endpoint_deterministic_fingerprint():
    """Exact same canonical endpoint produces identical SHA256 fingerprint."""
    spec1 = EndpointSpec(
        provider_id="postgresql",
        host="db.example.internal",
        port=5432,
        database_name="prod_db",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="app_user", password_ref="vault://p1"),
    )
    spec2 = EndpointSpec(
        provider_id="postgresql",
        host="db.example.internal",
        port=5432,
        database_name="prod_db",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="app_user", password_ref="vault://p1"),
    )

    fp1 = compute_endpoint_fingerprint(spec1)
    fp2 = compute_endpoint_fingerprint(spec2)
    assert fp1 == fp2
    assert len(fp1) == 64


def test_02_field_ordering_invariance():
    """Dictionaries with different key insertion orders produce identical fingerprint."""
    spec1 = EndpointSpec(
        provider_id="oracle",
        host="oracle-host",
        port=1521,
        database_name="FREEPDB1",
        options={"z_param": 100, "a_param": "first", "m_param": True},
    )
    spec2 = EndpointSpec(
        provider_id="oracle",
        host="oracle-host",
        port=1521,
        database_name="FREEPDB1",
        options={"a_param": "first", "m_param": True, "z_param": 100},
    )

    fp1 = compute_endpoint_fingerprint(spec1)
    fp2 = compute_endpoint_fingerprint(spec2)
    assert fp1 == fp2


def test_03_distinct_endpoints_produce_distinct_fingerprints():
    """Two different endpoints produce distinct fingerprints."""
    spec_pg = EndpointSpec(provider_id="postgresql", host="pg-host", port=5432, database_name="db1")
    spec_mysql = EndpointSpec(provider_id="mysql", host="mysql-host", port=3306, database_name="db1")
    spec_pg_port = EndpointSpec(provider_id="postgresql", host="pg-host", port=5433, database_name="db1")

    fp_pg = compute_endpoint_fingerprint(spec_pg)
    fp_mysql = compute_endpoint_fingerprint(spec_mysql)
    fp_pg_port = compute_endpoint_fingerprint(spec_pg_port)

    assert fp_pg != fp_mysql
    assert fp_pg != fp_pg_port
    assert fp_mysql != fp_pg_port


def test_04_arbitrary_runtime_objects_canonicalized_without_memory_addresses():
    """Arbitrary runtime objects in options are canonicalized deterministically without memory addresses."""
    obj1 = ArbitraryMockConnection("conn1")
    obj2 = ArbitraryMockConnection("conn2")

    # In raw python, str(obj1) -> '<...ArbitraryMockConnection object at 0x...>'
    assert "0x" in str(obj1)

    spec1 = EndpointSpec(provider_id="sap_application", host="sap-host", options={"db_connection": obj1})
    spec2 = EndpointSpec(provider_id="sap_application", host="sap-host", options={"db_connection": obj2})

    # Both have the same type 'ArbitraryMockConnection', so they canonicalize deterministically
    fp1 = compute_endpoint_fingerprint(spec1)
    fp2 = compute_endpoint_fingerprint(spec2)
    assert fp1 == fp2

    # Canonical data contains 'type:ArbitraryMockConnection', NOT memory address
    canon = canonicalize_for_fingerprint(spec1.sanitized_dict())
    assert canon["options"]["db_connection"] == "type:ArbitraryMockConnection"
    assert "0x" not in canon["options"]["db_connection"]


def test_05_secret_material_strictly_redacted():
    """Secret fields are redacted to [REDACTED] and never appear in canonical fingerprint payload."""
    spec = EndpointSpec(
        provider_id="postgres",
        host="pg-host",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="admin", password_ref="my_super_secret_password"),
        options={"api_key": "secret_token_12345", "client_secret": "xyz_secret"},
    )
    canon = canonicalize_for_fingerprint(spec.sanitized_dict())

    # Verify options are redacted
    assert canon["options"]["api_key"] == "[REDACTED]"
    assert canon["options"]["client_secret"] == "[REDACTED]"
    assert "secret_token_12345" not in str(canon)
    assert "xyz_secret" not in str(canon)
