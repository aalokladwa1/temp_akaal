"""
Unit tests for akaalEngine.connection.sessions
==============================================
Verifies session creation, lease scoping, rollback reset, and lifecycle management.
"""

import pytest

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.session import (
    IsolationLevel,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.connection.sessions.factory import SessionFactory
from akaalEngine.connection.sessions.lifecycle import SessionLifecycleManager
from akaalEngine.connection.sessions.reset import SessionResetManager


def test_session_factory_and_lease_lifecycle():
    factory = SessionFactory()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.SOURCE)
    req = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)

    handle, route = factory.create_physical_session(req)
    assert handle.session_id.startswith("sess-")
    assert handle.provider_id == "sqlite"
    assert handle.physical_connection is not None

    lifecycle = SessionLifecycleManager()
    lease = lifecycle.checkout_lease(handle, req, borrower_id="test-worker")

    assert lease.is_valid() is True
    assert lease.borrower_id == "test-worker"
    assert lease.purpose == SessionPurpose.BULK_SOURCE_READ

    # Verify native connection handle is retrievable via lease
    conn = lease.get_physical_handle()
    assert conn is not None

    # Test physical execution
    cur = conn.cursor()
    cur.execute("CREATE TABLE test_table (id INT, val TEXT)")
    cur.execute("INSERT INTO test_table VALUES (1, 'alpha')")
    cur.close()

    # Release and reset session
    strategy = SQLiteProviderStrategy()
    is_clean = lifecycle.release_lease(lease, strategy)
    assert is_clean is True

    # Validate clean session
    assert lifecycle.validate_lease(lease, strategy) is False  # Lease checked in, no longer active borrower

    route.close()
    strategy.close(handle.physical_connection)


def test_session_reset_poisoned_destruction():
    factory = SessionFactory()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.SOURCE)
    req = SessionRequest(purpose=SessionPurpose.METADATA, endpoint_spec=spec)

    handle, route = factory.create_physical_session(req)
    handle.is_poisoned = True

    strategy = SQLiteProviderStrategy()
    is_clean = SessionResetManager.reset_and_clean_session(handle, strategy)
    assert is_clean is False
    assert handle.is_closed is True
    assert handle.physical_connection is None
    route.close()
