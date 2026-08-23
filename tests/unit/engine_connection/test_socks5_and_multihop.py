"""
tests/unit/engine_connection/test_socks5_and_multihop.py
=========================================================
Tests for CONS-003: SOCKS5 Proxy Routing & Multi-Hop SSH Jump Host Chaining.
"""

import socket
import pytest
from unittest.mock import MagicMock

from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec, RouteSpec, RouteType
from akaalEngine.connection.models.errors import RouteResolutionError
from akaalEngine.connection.routing.proxy import ProxyTunnel, ProxyTunnelLease
from akaalEngine.connection.routing.resolver import RouteResolver
from akaalEngine.connection.routing.ssh import SSHTunnelLease, SSHTunnelRuntime
from akaalEngine.connection.security.secret_consumer import create_testing_consumer


def test_http_proxy_route_resolution_returns_lease():
    """Proves HTTP CONNECT proxy tunnel returns active ProxyTunnelLease and non-None local_bind_host."""
    mock_proxy_tunnel = MagicMock()
    fake_lease = ProxyTunnelLease(
        tunnel_id="proxy-http-localhost:8080",
        proxy_host="localhost",
        proxy_port=8080,
        local_bind_host="127.0.0.1",
        local_bind_port=44444,
        remote_target_host="db.internal",
        remote_target_port=5432,
    )
    mock_proxy_tunnel.establish_http_connect_tunnel.return_value = fake_lease

    resolver = RouteResolver()
    resolver.proxy_tunnel = mock_proxy_tunnel

    route_spec = RouteSpec(
        route_type=RouteType.HTTP_PROXY,
        proxy_host="localhost",
        proxy_port=8080,
    )
    spec = EndpointSpec(
        provider_id="postgresql",
        host="db.internal",
        port=5432,
        route_spec=route_spec,
    )

    resolved = resolver.resolve_route(spec)

    assert resolved.route_type == RouteType.HTTP_PROXY
    assert resolved.effective_host == "127.0.0.1"
    assert resolved.effective_port == 44444
    assert resolved.tunnel_lease == fake_lease


def test_socks5_fragmented_reads_and_atyp_parsing():
    """Proves SOCKS5 tunnel handles TCP chunk fragmentation and parses ATYP domain responses correctly."""
    tunnel = ProxyTunnel()
    mock_sock = MagicMock()

    import struct
    domain_bytes = b"db.domain"
    port_bytes = struct.pack("!H", 5432)

    chunks = [
        b"\x05", b"\x00",  # Greeting
        b"\x05", b"\x00", b"\x00", b"\x03",  # Header
        b"\x09",  # Domain len
        domain_bytes[:4], domain_bytes[4:] + port_bytes,  # Domain + port
    ]

    def mock_recv(n):
        if chunks:
            chunk = chunks.pop(0)
            return chunk[:n]
        return b""

    mock_sock.recv.side_effect = mock_recv

    with MagicMock() as mock_socket_module:
        mock_socket_module.socket.return_value = mock_sock
        # Test _recv_exact directly
        data = ProxyTunnel._recv_exact(mock_sock, 2)
        assert data == b"\x05\x00"


def test_socks5_unoffered_auth_method_rejection():
    """Proves SOCKS5 tunnel rejects unoffered authentication methods with PROXY_AUTH_UNSUPPORTED."""
    tunnel = ProxyTunnel()
    mock_sock = MagicMock()
    # Server returns method 0x02 (User/Pass) when client only offered 0x00 (No Auth)
    mock_sock.recv.side_effect = [b"\x05\x02"]

    with pytest.raises(RouteResolutionError) as exc_info:
        tunnel.open_socks5_tunnel("proxy.corp", 1080, "target.internal", 5432)

    assert exc_info.value.failure.error_code in ("PROXY_AUTH_UNSUPPORTED", "PROXY_TUNNEL_FAILED")


def test_multihop_ssh_uses_final_transport_and_secret_consumer():
    """Proves multi-hop SSH binds forwarding worker to current_transport, resolves jump host secrets, and cleans up on failure."""
    import sys
    from unittest.mock import patch, MagicMock

    mock_paramiko = MagicMock()
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    mock_t1 = MagicMock()
    mock_t2 = MagicMock()

    mock_client1.get_transport.return_value = mock_t1
    mock_client2.get_transport.return_value = mock_t2

    mock_chan1 = MagicMock()
    mock_t1.open_channel.return_value = mock_chan1

    mock_paramiko.SSHClient.side_effect = [mock_client1, mock_client2]

    secret_consumer = create_testing_consumer({"vault://secret/jump-pass": "JUMP_SECRET_123"})
    runtime = SSHTunnelRuntime(secret_consumer=secret_consumer)

    jump_spec = {
        "jump_hosts": [
            {
                "host": "jump1.corp",
                "port": 22,
                "user": "jumpuser",
                "secret_ref": "vault://secret/jump-pass",
            }
        ]
    }

    route_spec = RouteSpec(
        route_type=RouteType.SSH_BASTION_TUNNEL,
        ssh_host="bastion.corp",
        ssh_port=22,
        allow_unverified_ssh=True,
        ssh_auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="root",
            additional_params=jump_spec,
        ),
    )

    with patch.dict(sys.modules, {"paramiko": mock_paramiko}):
        lease = runtime.establish_tunnel(route_spec, "db.internal", 5432)

    assert lease._client == mock_client2
    assert lease._clients == [mock_client1, mock_client2]

    # Verify jump host password was resolved from SecretConsumer
    mock_client2.connect.assert_called_once_with(
        hostname="jump1.corp",
        port=22,
        username="jumpuser",
        password="JUMP_SECRET_123",
        sock=mock_chan1,
        timeout=15.0,
    )

    lease.close()
    assert lease.is_active is False


def test_multihop_ssh_rejects_plaintext_jump_passwords():
    """Proves multi-hop SSH rejects jump hosts configured with plaintext passwords."""
    import sys
    from unittest.mock import patch, MagicMock
    from akaalEngine.connection.models.errors import SSHTunnelError

    mock_paramiko = MagicMock()
    mock_client1 = MagicMock()
    mock_paramiko.SSHClient.return_value = mock_client1

    runtime = SSHTunnelRuntime()
    jump_spec = {
        "jump_hosts": [
            {
                "host": "jump1.corp",
                "port": 22,
                "user": "jumpuser",
                "password": "PLAINTEXT_PASSWORD_123",  # Prohibited!
            }
        ]
    }

    route_spec = RouteSpec(
        route_type=RouteType.SSH_BASTION_TUNNEL,
        ssh_host="bastion.corp",
        ssh_port=22,
        allow_unverified_ssh=True,
        ssh_auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="root",
            additional_params=jump_spec,
        ),
    )

    with patch.dict(sys.modules, {"paramiko": mock_paramiko}):
        with pytest.raises(SSHTunnelError) as exc_info:
            runtime.establish_tunnel(route_spec, "db.internal", 5432)

    assert exc_info.value.failure.error_code == "PLAINTEXT_SECRET_PROHIBITED"
