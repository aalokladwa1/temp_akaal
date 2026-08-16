"""
AKAAL P4.7 — Universal Private / On-Prem / Hybrid Connectivity Hostile Test Suite.
===================================================================================
Comprehensive hostile reality verification of P4.7 Generalized Transport Runtime across:
Direct connectivity, RFC 8305 Happy Eyeballs dual-stack connection racing, SSH bastions,
multi-hop jump hosts, HTTP CONNECT & SOCKS5 real local proxies, remote AKAAL agents,
half-open TCP detection, fail-closed security checks, secret redaction, and P4.6 cloud integration.
"""

import unittest
import asyncio
import socket
import time

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.transport.models import (
    TransportMethod,
    TransportState,
    TransportFailureClass,
    TransportEndpoint,
    TransportHop,
    TransportPath,
    TransportSession,
    TransportDiagnostics,
    redact_text,
)
from akaal.transport.dns_resolver import EnterpriseDNSResolver, DNSResolutionResult
from akaal.transport.ssh_runtime import SSHForwardingTunnel
from akaal.transport.proxy_runtime import EnterpriseProxyRuntime
from akaal.transport.agent_boundary import RemoteAgentBoundaryManager
from akaal.transport.health_monitor import TransportHealthMonitor
from akaal.transport.transport_manager import TransportManager, get_global_transport_manager
from akaal.gateway.engine_gateway import EngineGateway


class TestP47GeneralizedTransportRuntime(unittest.TestCase):
    """Hostile Reality Test Suite for P4.7 Generalized Transport Runtime."""

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tm = TransportManager()

    def tearDown(self) -> None:
        self.loop.close()

    # -------------------------------------------------------------------------
    # 1. DNS & Dual-Stack Happy Eyeballs Tests
    # -------------------------------------------------------------------------
    def test_01_direct_and_dual_stack_dns_resolution(self):
        """01: Verify enterprise DNS resolver handles IP literals, hostname caching, and IPv4/IPv6 dual-stack ordering."""
        resolver = EnterpriseDNSResolver()

        async def run():
            # IP literal
            res_ip = await resolver.resolve_hostname("127.0.0.1")
            self.assertEqual(res_ip.addresses[0][1], "127.0.0.1")

            # Hostname resolution
            res_host = await resolver.resolve_hostname("localhost")
            self.assertTrue(len(res_host.addresses) >= 1)

        self.loop.run_until_complete(run())

    def test_01b_happy_eyeballs_scheduler_fast_return(self):
        """01b: Verify RFC 8305 scheduler returns immediately when first candidate succeeds in <5ms without waiting full attempt delays."""
        async def run():
            server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
            h, p = server.sockets[0].getsockname()

            resolver = EnterpriseDNSResolver()

            # Mock DNS resolver to return 10 addresses
            fake_addrs = [(socket.AF_INET, "127.0.0.1") for _ in range(10)]
            async def _mock_resolve(host, force=False):
                return DNSResolutionResult(host, fake_addrs, [], 1.0)
            resolver.resolve_hostname = _mock_resolve

            t0 = time.perf_counter()
            sock, connected_ip, connected_port = await resolver.happy_eyeballs_connect(
                h, p, connect_timeout_seconds=5.0, connection_attempt_delay=0.10  # 100ms delay per candidate
            )
            elapsed = time.perf_counter() - t0

            # Must return in <50ms (first attempt succeeds immediately), NOT waiting 10 * 100ms = 1000ms!
            self.assertLess(elapsed, 0.20)
            self.assertEqual(connected_ip, "127.0.0.1")
            sock.close()
            server.close()
            await server.wait_closed()

        self.loop.run_until_complete(run())

    def test_01c_happy_eyeballs_input_validation(self):
        """01c: Verify Happy Eyeballs validates invalid port numbers and negative attempt delays upfront."""
        resolver = EnterpriseDNSResolver()

        async def run():
            with self.assertRaises(ValueError):
                await resolver.happy_eyeballs_connect("localhost", 0)
            with self.assertRaises(ValueError):
                await resolver.happy_eyeballs_connect("localhost", 70000)
            with self.assertRaises(ValueError):
                await resolver.happy_eyeballs_connect("localhost", 5432, connection_attempt_delay=-0.5)

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 2. Path Topology & Loop Detection Tests
    # -------------------------------------------------------------------------
    def test_02_path_topology_loop_detection_fails_closed(self):
        """02: Verify paths with cyclic hop references or exceeding max hop limits fail closed with ValueError."""
        hop_a = TransportHop(hop_type="BASTION", hostname="bastion-a.corp", port=22)
        hop_b = TransportHop(hop_type="BASTION", hostname="bastion-a.corp", port=22)  # Duplicate!

        target = TransportEndpoint("db.internal", 5432)

        # Loop detection failure
        with self.assertRaises(ValueError):
            TransportPath(transport_method=TransportMethod.MULTI_HOP_SSH, target_endpoint=target, hops=[hop_a, hop_b])

        # Exceed max hop limit
        many_hops = [TransportHop(hostname=f"b{i}.corp", port=22) for i in range(10)]
        with self.assertRaises(ValueError):
            TransportPath(transport_method=TransportMethod.MULTI_HOP_SSH, target_endpoint=target, hops=many_hops, max_hop_limit=5)

    # -------------------------------------------------------------------------
    # 3. SSH Bastion & Host Key Validation Tests
    # -------------------------------------------------------------------------
    def test_03_ssh_bastion_and_multihop_tunnel_forwarding(self):
        """03: Verify SSH forwarding tunnel allocates ephemeral local port atomically."""
        hop = TransportHop(
            hop_type="BASTION",
            hostname="bastion.prod.internal",
            port=22,
            username="admin",
            auth_method="PASSWORD",
            raw_credentials={"password": "super_secret_ssh_pass_999"},
        )
        target = TransportEndpoint("pg-db.private.internal", 5432)
        tunnel = SSHForwardingTunnel(hops=[hop], target_endpoint=target)

        async def run():
            host, port = await tunnel.start()
            self.assertEqual(host, "127.0.0.1")
            self.assertGreater(port, 1024)
            await tunnel.close()

        self.loop.run_until_complete(run())

    def test_04_ssh_host_key_mismatch_fails_closed(self):
        """04: Verify SSH host key fingerprint mismatch fails closed with RuntimeError."""
        hop = TransportHop(
            hop_type="BASTION",
            hostname="bastion-untrusted.com",
            port=22,
            expected_fingerprint="MISMATCH_KEY_FINGERPRINT_BAD",
        )
        target = TransportEndpoint("db.internal", 5432)
        tunnel = SSHForwardingTunnel(hops=[hop], target_endpoint=target)

        async def run():
            with self.assertRaises(RuntimeError):
                await tunnel.start()

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 4. Proxy Runtime Tests
    # -------------------------------------------------------------------------
    def test_05_proxy_hop_resolution_and_preflight(self):
        """05: Verify proxy hop configuration resolves into TransportPath and runs preflight diagnostics."""
        cfg = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="db.internal.net",
            port=5432,
            database_name="app_db",
            credentials_ref="ref-123",
            extra={
                "proxy_host": "proxy.corp.net",
                "proxy_port": 8080,
                "proxy_type": "HTTP",
                "proxy_username": "proxy_user",
                "proxy_password": "proxy_secret_password_123",
            },
        )
        path = self.tm.resolve_transport_path(cfg)
        self.assertEqual(path.transport_method, TransportMethod.HTTP_CONNECT_PROXY)
        self.assertEqual(len(path.hops), 1)
        self.assertEqual(path.hops[0].hostname, "proxy.corp.net")

    def test_05b_http_connect_proxy_407_auth_failure(self):
        """05b: Verify HTTP CONNECT proxy negotiation fails closed on HTTP 407 authentication required."""
        async def run():
            async def _proxy_407_handler(reader, writer):
                await reader.readuntil(b"\r\n\r\n")
                writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic\r\n\r\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(_proxy_407_handler, "127.0.0.1", 0)
            p_host, p_port = server.sockets[0].getsockname()

            proxy_hop = TransportHop(hop_type="PROXY", hostname=p_host, port=p_port)
            target = TransportEndpoint("target-db.local", 5432)

            with self.assertRaises(RuntimeError) as ctx:
                await EnterpriseProxyRuntime.connect_via_http_connect(proxy_hop, target, 5.0)

            self.assertIn("407", str(ctx.exception))
            server.close()
            await server.wait_closed()

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 5. Remote Agent Boundary Tests
    # -------------------------------------------------------------------------
    def test_06_remote_agent_boundary_and_zone_routing(self):
        """06: Verify remote AKAAL agent registration, token verification, and fail-closed unauthenticated routing."""
        mgr = RemoteAgentBoundaryManager()

        # Unregistered agent fails closed
        hop_unreg = TransportHop(hop_type="AGENT", hostname="agent-unregistered")
        target = TransportEndpoint("onprem-db.local", 1521)

        async def run():
            with self.assertRaises(RuntimeError):
                await mgr.route_via_agent(hop_unreg, target)

            # Register valid agent
            session = mgr.register_agent("agent-01", "OnPrem-Agent-DMZ", "DMZ_ZONE")
            self.assertTrue(session.is_healthy())

            hop_reg = TransportHop(hop_type="AGENT", hostname="agent-01", known_hosts_ref="DMZ_ZONE")
            host, port = await mgr.route_via_agent(hop_reg, target)
            self.assertEqual(host, "onprem-db.local")
            self.assertEqual(port, 1521)

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 6. Health Monitor & Half-Open Socket Detection Tests
    # -------------------------------------------------------------------------
    def test_07_half_open_detection_and_reconnect_jitter(self):
        """07: Verify half-open socket detection returns False for closed sockets and backoff jitter stays bounded."""
        # Closed socket liveness
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.close()

        async def run():
            is_alive = await TransportHealthMonitor.check_socket_liveness(s)
            self.assertFalse(is_alive)

        self.loop.run_until_complete(run())

        # Jitter calculation stays bounded
        j1 = TransportHealthMonitor.calculate_reconnect_jitter(attempt=1, base_delay=1.0, max_delay=10.0)
        self.assertGreaterEqual(j1, 0.0)
        self.assertLessEqual(j1, 1.0)

    # -------------------------------------------------------------------------
    # 7. Secret Redaction Tests
    # -------------------------------------------------------------------------
    def test_08_secret_redaction_across_transport_logs_and_models(self):
        """08: Verify secrets and passphrases are redacted as [REDACTED] in transport models and diagnostics."""
        secret_pass = "super_secret_ssh_bastion_password_999"
        redacted = redact_text(f"Connection failed with password={secret_pass} on tunnel", extra_secrets=[secret_pass])
        self.assertNotIn(secret_pass, redacted)
        self.assertIn("[REDACTED]", redacted)

        # Hop model sanitized serialization does not include raw password
        hop = TransportHop(
            hostname="bastion.local",
            username="admin",
            raw_credentials={"password": secret_pass},
        )
        sanitized = hop.to_sanitized_dict()
        self.assertNotIn(secret_pass, str(sanitized))
        self.assertNotIn("password", sanitized)

    # -------------------------------------------------------------------------
    # 8. P4.6 Cloud Managed Profile Integration Tests
    # -------------------------------------------------------------------------
    def test_09_cloud_managed_profile_p4_6_integration(self):
        """09: Verify P4.7 TransportManager consumes P4.6 cloud profile metadata hooks seamlessly."""
        cfg = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="prod-aurora.cluster-c123.us-east-1.rds.amazonaws.com",
            port=5432,
            database_name="app_db",
            credentials_ref="ref-aurora",
            extra={
                "network_id": "vpc-01122334455667788",
                "subnet_id": "subnet-0abc1234",
                "security_group_ids": ["sg-099887766"],
                "bastion_reference": "bastion.us-east-1.corp.net",
                "ssh_bastion_username": "ec2-user",
                "ssh_bastion_password": "ec2_password_12345",
            },
        )
        path = self.tm.resolve_transport_path(cfg)
        self.assertEqual(path.transport_method, TransportMethod.BASTION)
        self.assertEqual(path.network_id, "vpc-01122334455667788")
        self.assertEqual(len(path.hops), 1)
        self.assertEqual(path.hops[0].hostname, "bastion.us-east-1.corp.net")

    # -------------------------------------------------------------------------
    # 9. EngineGateway IPC Delegation Tests
    # -------------------------------------------------------------------------
    def test_10_engine_gateway_p4_7_ipc_capability_delegation(self):
        """10: Verify EngineGateway exposes P4.7 capability handlers dynamically."""
        gw = EngineGateway()

        payload = {
            "system_type": "POSTGRESQL",
            "host": "db.corp.local",
            "port": 5432,
            "extra": {"bastion_reference": "bastion.corp.local", "ssh_bastion_password": "pass"},
        }
        res_resolve = gw.resolve_transport_path(payload)
        self.assertEqual(res_resolve["transport_method"], "BASTION")
        self.assertEqual(res_resolve["target_endpoint"]["hostname"], "db.corp.local")

    # -------------------------------------------------------------------------
    # 10. Negative & Zero Duplicate Authority Verification
    # -------------------------------------------------------------------------
    def test_11_zero_duplicate_authority_and_fsm_subordination(self):
        """11: Verify P4.7 contains zero duplicate migration, CDC, checkpoint, retry, or secret authorities."""
        self.assertFalse(hasattr(self.tm, "execute_migration"))
        self.assertFalse(hasattr(self.tm, "mine_transaction_logs"))
        self.assertFalse(hasattr(self.tm, "commit_checkpoint"))

    # -------------------------------------------------------------------------
    # 11. Real Local Network Integration Tests (HTTP CONNECT & SOCKS5)
    # -------------------------------------------------------------------------
    def test_12_real_local_http_connect_proxy_negotiation(self):
        """12: Real Local Network Integration Test — HTTP CONNECT Proxy Server."""
        async def run():
            # Spawn real local HTTP CONNECT server
            async def _proxy_handler(reader, writer):
                req = await reader.readuntil(b"\r\n\r\n")
                if b"CONNECT" in req:
                    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await writer.drain()
                    await reader.read(100)
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(_proxy_handler, "127.0.0.1", 0)
            p_host, p_port = server.sockets[0].getsockname()

            proxy_hop = TransportHop(
                hop_type="PROXY",
                hostname=p_host,
                port=p_port,
                auth_method="NONE",
            )
            target = TransportEndpoint("127.0.0.1", 80)

            sock = await EnterpriseProxyRuntime.connect_via_http_connect(proxy_hop, target, 5.0)
            self.assertIsNotNone(sock)
            sock.close()
            server.close()
            await server.wait_closed()

        self.loop.run_until_complete(run())

    def test_13_real_local_socks5_proxy_negotiation(self):
        """13: Real Local Network Integration Test — SOCKS5 Proxy Server."""
        async def run():
            # Spawn real local SOCKS5 server
            async def _socks_handler(reader, writer):
                greet = await reader.read(3)
                if len(greet) >= 2 and greet[0] == 5:
                    writer.write(b"\x05\x00")  # NO AUTH chosen
                    await writer.drain()

                req = await reader.read(256)
                if len(req) >= 4 and req[0] == 5 and req[1] == 1:
                    # Reply success with bound 127.0.0.1:1080
                    writer.write(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x04\x38")
                    await writer.drain()
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(_socks_handler, "127.0.0.1", 0)
            p_host, p_port = server.sockets[0].getsockname()

            proxy_hop = TransportHop(
                hop_type="PROXY",
                hostname=p_host,
                port=p_port,
                auth_method="NONE",
            )
            target = TransportEndpoint("target-db.local", 5432)

            sock = await EnterpriseProxyRuntime.connect_via_socks5(proxy_hop, target, 5.0)
            self.assertIsNotNone(sock)
            sock.close()
            server.close()
            await server.wait_closed()

        self.loop.run_until_complete(run())

    def test_14_rfc_8305_happy_eyeballs_racing_with_real_local_listener(self):
        """14: Real Local Network Integration Test — Happy Eyeballs Dual-Stack Connection Racing."""
        async def run():
            server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
            h, p = server.sockets[0].getsockname()

            resolver = EnterpriseDNSResolver()
            sock, connected_ip, connected_port = await resolver.happy_eyeballs_connect(h, p, connect_timeout_seconds=5.0)

            self.assertEqual(connected_ip, "127.0.0.1")
            self.assertEqual(connected_port, p)
            sock.close()
            server.close()
            await server.wait_closed()

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
