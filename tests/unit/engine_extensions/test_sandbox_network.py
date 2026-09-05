"""
tests.unit.engine_extensions.test_sandbox_network
==================================================
Hostile verification of Blocker #4 Network Sandbox Enforcement:
- Model B: Host-Mediated Network Execution is the real security boundary.
- Reuse of canonical RouteSpec/EndpointSpec and tenant isolation concepts.
- Zero-trust default-deny when no network destinations are granted.
- Protection against cloud metadata endpoints (169.254.169.254).
- Loopback isolation: blocked by default, permitted only when explicitly granted.
- Cross-tenant route request rejection.
- In-worker defense-in-depth guard intercepts direct raw socket calls.
- Truthful reporting of HOST_MEDIATED access model vs OS isolation boundary.
"""

from __future__ import annotations

import socket
import pytest

from akaalEngine.extensions.sandbox.host_mediated import (
    HostMediatedNetworkService,
)
from akaalEngine.extensions.sandbox.permissions import GrantedPermissions
from akaalEngine.extensions.sandbox.worker_guards import DirectIOException, install_worker_network_guard


def test_allowed_destination_succeeds():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"api.example.com", "db.corp.internal:5432"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_destination("api.example.com", 443)
    assert allowed is True
    assert "permitted" in diag

    allowed2, diag2 = svc.validate_destination("db.corp.internal", 5432)
    assert allowed2 is True


def test_unapproved_destination_fails():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"api.example.com"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_destination("evil.attacker.com", 443)
    assert allowed is False
    assert "not in granted destinations" in diag


def test_wrong_port_fails():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"db.corp.internal:5432"})
    )
    svc = HostMediatedNetworkService(granted)

    # Port 5432 is granted, port 3306 must fail
    allowed, diag = svc.validate_destination("db.corp.internal", 3306)
    assert allowed is False


def test_zero_trust_default_deny_when_no_destinations_granted():
    granted = GrantedPermissions.empty()
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_destination("api.example.com", 443)
    assert allowed is False
    assert "no network destinations granted" in diag


def test_loopback_is_blocked_by_default():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"api.example.com"})
    )
    svc = HostMediatedNetworkService(granted)

    for loopback in ("127.0.0.1", "localhost", "::1", "127.0.1.1"):
        allowed, diag = svc.validate_destination(loopback, 8080)
        assert allowed is False
        assert "loopback interface" in diag


def test_loopback_is_permitted_only_when_explicitly_granted():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"127.0.0.1:8080"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_destination("127.0.0.1", 8080)
    assert allowed is True


def test_cloud_metadata_endpoint_is_strictly_blocked():
    # Even if an extension tries to request or guess cloud metadata endpoints, they are forbidden
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"169.254.169.254", "metadata.google.internal"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_destination("169.254.169.254", 80)
    assert allowed is False
    assert "cloud metadata endpoint" in diag

    allowed2, diag2 = svc.validate_destination("metadata.google.internal", 80)
    assert allowed2 is False
    assert "cloud metadata endpoint" in diag2


def test_cross_tenant_route_request_is_rejected():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"pg.acme.corp:5432"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_route_request(
        target_provider_id="postgresql",
        endpoint_host="pg.acme.corp",
        endpoint_port=5432,
        caller_tenant_id="tenant-attacker",
        expected_tenant_id="tenant-victim",
    )
    assert allowed is False
    assert "Cross-tenant route request rejected" in diag


def test_same_tenant_route_request_succeeds_when_granted():
    granted = GrantedPermissions(
        network_egress_hosts=frozenset({"pg.acme.corp:5432"})
    )
    svc = HostMediatedNetworkService(granted)

    allowed, diag = svc.validate_route_request(
        target_provider_id="postgresql",
        endpoint_host="pg.acme.corp",
        endpoint_port=5432,
        caller_tenant_id="tenant-acme",
        expected_tenant_id="tenant-acme",
    )
    assert allowed is True


def test_worker_network_guard_intercepts_direct_raw_socket():
    """
    install_worker_network_guard() monkey-patches socket.socket.connect at the CLASS
    level -- process-global, not scoped to this test. Without an explicit uninstall in
    finally, every subsequent test in this pytest session (potentially in a completely
    different test file) would be unable to open any real socket -- reproduced as a real
    regression (Redis-backed checkpoint tests failing later in the same session) before
    this fix. In production this guard only ever runs inside an isolated sandboxed CHILD
    process whose exit naturally undoes the patch; a test in the long-lived pytest process
    has no such natural boundary and must restore it explicitly.
    """
    from akaalEngine.extensions.sandbox.worker_guards import uninstall_worker_network_guard

    install_worker_network_guard()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(DirectIOException) as exc_info:
                s.connect(("127.0.0.1", 80))
            assert "Direct raw socket connection" in str(exc_info.value)
        finally:
            s.close()
    finally:
        uninstall_worker_network_guard()


def test_worker_network_guard_is_fully_restored_after_uninstall():
    """Proves the guard doesn't leak: after uninstall, a real (failing, but non-guard) connect error occurs."""
    from akaalEngine.extensions.sandbox.worker_guards import uninstall_worker_network_guard

    install_worker_network_guard()
    uninstall_worker_network_guard()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        with pytest.raises(Exception) as exc_info:
            # Port 1 is essentially guaranteed closed/unreachable -- proves this is a real
            # connection attempt (a real OSError/ConnectionRefusedError/timeout), not the
            # guard's DirectIOException, since the guard should no longer be installed.
            s.connect(("127.0.0.1", 1))
        assert not isinstance(exc_info.value, DirectIOException)
    finally:
        s.close()
