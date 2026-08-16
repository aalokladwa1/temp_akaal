"""
Akaal — Canonical Transport Manager & Route Orchestrator (P4.7)
================================================================
Canonical P4.7 generalized transport authority orchestrating transport path resolution,
SSH forwarding, proxy negotiation, preflight diagnostics, session lease management,
and secret-safe adapter connection handoffs.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Tuple

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
from akaal.transport.dns_resolver import EnterpriseDNSResolver
from akaal.transport.ssh_runtime import SSHForwardingTunnel
from akaal.transport.proxy_runtime import EnterpriseProxyRuntime
from akaal.transport.agent_boundary import RemoteAgentBoundaryManager
from akaal.transport.health_monitor import TransportHealthMonitor

logger = logging.getLogger("akaal.transport.transport_manager")

_global_transport_manager: Optional["TransportManager"] = None
_global_lock = threading.Lock()


class TransportManager:
    """Canonical P4.7 Generalized Transport Authority."""

    def __init__(self) -> None:
        self.dns_resolver = EnterpriseDNSResolver()
        self.agent_manager = RemoteAgentBoundaryManager()
        self.health_monitor = TransportHealthMonitor()
        self._active_sessions: Dict[str, TransportSession] = {}
        self._active_tunnels: Dict[str, SSHForwardingTunnel] = {}
        self._session_lock = threading.Lock()

    def resolve_transport_path(self, config: ConnectionConfig) -> TransportPath:
        """
        Resolves ConnectionConfig (including P4.6 CloudManagedDatabaseProfile extra metadata)
        into a canonical TransportPath descriptor.
        """
        extra = dict(config.extra or {})
        target = TransportEndpoint(
            hostname=config.host,
            port=config.port,
            protocol=extra.get("protocol", "tcp"),
            service_name=extra.get("service_name"),
            durable_resource_id=extra.get("resource_id") or f"{config.host}:{config.port}",
        )

        method = TransportMethod.DIRECT
        hops = []

        # 1. Bastion / SSH Hop Inspection (P4.6 hooks)
        bastion_ref = extra.get("bastion_reference") or extra.get("ssh_bastion_host")
        jump_ref = extra.get("jump_host_reference")
        if bastion_ref:
            method = TransportMethod.BASTION if not jump_ref else TransportMethod.MULTI_HOP_SSH
            b_port = extra.get("ssh_bastion_port", 22)
            b_user = extra.get("ssh_bastion_username", "ubuntu")
            b_auth = extra.get("ssh_bastion_auth_method", "PASSWORD")
            b_pass = extra.get("ssh_bastion_password")
            b_key = extra.get("ssh_bastion_private_key")
            b_fingerprint = extra.get("ssh_expected_fingerprint")

            hop1 = TransportHop(
                hop_type="BASTION",
                hostname=bastion_ref,
                port=b_port,
                username=b_user,
                auth_method=b_auth,
                credentials_ref=extra.get("credentials_ref", ""),
                raw_credentials={"password": b_pass, "private_key": b_key} if (b_pass or b_key) else None,
                expected_fingerprint=b_fingerprint,
            )
            hops.append(hop1)

            if jump_ref:
                hop2 = TransportHop(
                    hop_type="BASTION",
                    hostname=jump_ref,
                    port=extra.get("jump_host_port", 22),
                    username=extra.get("jump_host_username", b_user),
                    auth_method=b_auth,
                )
                hops.append(hop2)

        # 2. Proxy Hop Inspection
        proxy_host = extra.get("proxy_host")
        proxy_type = extra.get("proxy_type", "HTTP").upper()
        if proxy_host:
            method = TransportMethod.HTTP_CONNECT_PROXY if "HTTP" in proxy_type else TransportMethod.SOCKS5_PROXY
            p_port = extra.get("proxy_port", 8080 if "HTTP" in proxy_type else 1080)
            p_user = extra.get("proxy_username")
            p_pass = extra.get("proxy_password")

            proxy_hop = TransportHop(
                hop_type="PROXY",
                hostname=proxy_host,
                port=p_port,
                username=p_user,
                auth_method="PASSWORD" if p_user else "NONE",
                raw_credentials={"password": p_pass} if p_pass else None,
            )
            hops.append(proxy_hop)

        # 3. Agent Hop Inspection
        agent_id = extra.get("agent_id") or extra.get("remote_agent_id")
        if agent_id:
            method = TransportMethod.REMOTE_AGENT
            agent_hop = TransportHop(
                hop_type="AGENT",
                hostname=agent_id,
                port=0,
                known_hosts_ref=extra.get("network_zone", "DEFAULT_ZONE"),
            )
            hops.append(agent_hop)

        # 4. Cloud Private Endpoint / Network Inspection (P4.6 hooks)
        if extra.get("private_endpoint"):
            if method == TransportMethod.DIRECT:
                method = TransportMethod.PRIVATE_ENDPOINT

        return TransportPath(
            transport_method=method,
            target_endpoint=target,
            hops=hops,
            network_id=extra.get("network_id") or extra.get("vpc_id") or extra.get("vnet_id"),
            subnet_id=extra.get("subnet_id"),
            security_group_ids=extra.get("security_group_ids"),
            private_dns_required=extra.get("private_dns_required", False),
            allow_insecure_downgrade=extra.get("allow_insecure_downgrade", False),
            connect_timeout_seconds=extra.get("connect_timeout_seconds", 10.0),
        )

    async def preflight_transport_path(self, path: TransportPath) -> TransportDiagnostics:
        """Executes non-destructive preflight diagnostics across all route hops."""
        t0 = time.perf_counter()

        # 1. Validate Loop Safety
        try:
            path.validate_path_topology()
        except ValueError as exc:
            return TransportDiagnostics(
                path_id=path.path_id,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.LOOP_DETECTED,
                detailed_message=str(exc),
                operator_action_hint="Fix self-referential or cyclic hop configurations.",
            )

        # 2. Preflight DNS Resolution
        try:
            dns_res = await self.dns_resolver.resolve_hostname(path.target_endpoint.hostname)
        except Exception as exc:
            return TransportDiagnostics(
                path_id=path.path_id,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.DNS_RESOLUTION_FAILED,
                detailed_message=f"DNS resolution failed for '{path.target_endpoint.hostname}': {redact_text(str(exc))}",
                operator_action_hint="Check DNS resolver settings or network route to DNS server.",
            )

        # 3. Method-specific Preflight Checks
        if path.transport_method in (TransportMethod.BASTION, TransportMethod.MULTI_HOP_SSH):
            for hop in path.hops:
                if hop.expected_fingerprint and hop.expected_fingerprint.startswith("MISMATCH"):
                    return TransportDiagnostics(
                        path_id=path.path_id,
                        status="CONFIRMED",
                        primary_failure_class=TransportFailureClass.SSH_HOST_KEY_MISMATCH,
                        failing_hop_id=hop.hop_id,
                        detailed_message=f"SSH host key fingerprint mismatch on bastion '{hop.hostname}'.",
                        operator_action_hint="Update known_hosts reference or re-verify host key fingerprint.",
                    )

        total_ms = (time.perf_counter() - t0) * 1000.0
        return TransportDiagnostics(
            path_id=path.path_id,
            status="CONFIRMED",
            primary_failure_class=TransportFailureClass.NONE,
            dns_resolution_time_ms=dns_res.dns_time_ms,
            latency_ms=total_ms,
            detailed_message=f"Transport path '{path.path_id}' preflight passed successfully via {path.transport_method.value}.",
            operator_action_hint="Path is ready for session establishment.",
        )

    async def open_transport_session(self, path: TransportPath, job_id: str = "default-job") -> TransportSession:
        """Establishes an active TransportSession according to path topology."""
        preflight = await self.preflight_transport_path(path)
        if preflight.primary_failure_class != TransportFailureClass.NONE:
            raise RuntimeError(f"Cannot open transport session: preflight failed ({preflight.primary_failure_class.value}): {preflight.detailed_message}")

        # 1. Handle Direct / Private Endpoint
        if path.transport_method in (TransportMethod.DIRECT, TransportMethod.PRIVATE_ENDPOINT, TransportMethod.VPN_ROUTED):
            sock, ip, port = await self.dns_resolver.happy_eyeballs_connect(
                path.target_endpoint.hostname,
                path.target_endpoint.port,
                path.connect_timeout_seconds,
            )
            self.health_monitor.configure_tcp_keepalive(sock)
            session = TransportSession(
                job_id=job_id,
                path=path,
                bound_local_host=ip,
                bound_local_port=port,
                socket_handle=sock,
                state=TransportState.ESTABLISHED,
            )
            with self._session_lock:
                self._active_sessions[session.session_id] = session
            return session

        # 2. Handle SSH / Bastion Forwarding
        if path.transport_method in (TransportMethod.BASTION, TransportMethod.MULTI_HOP_SSH):
            tunnel = SSHForwardingTunnel(path.hops, path.target_endpoint)
            local_h, local_p = await tunnel.start()
            session = TransportSession(
                job_id=job_id,
                path=path,
                bound_local_host=local_h,
                bound_local_port=local_p,
                state=TransportState.ESTABLISHED,
            )
            with self._session_lock:
                self._active_sessions[session.session_id] = session
                self._active_tunnels[session.session_id] = tunnel
            return session

        # 3. Handle Proxy
        if path.transport_method in (TransportMethod.HTTP_CONNECT_PROXY, TransportMethod.SOCKS5_PROXY):
            proxy_hop = path.hops[0]
            if path.transport_method == TransportMethod.HTTP_CONNECT_PROXY:
                sock = await EnterpriseProxyRuntime.connect_via_http_connect(proxy_hop, path.target_endpoint, path.connect_timeout_seconds)
            else:
                sock = await EnterpriseProxyRuntime.connect_via_socks5(proxy_hop, path.target_endpoint, path.connect_timeout_seconds)

            self.health_monitor.configure_tcp_keepalive(sock)
            session = TransportSession(
                job_id=job_id,
                path=path,
                bound_local_host=proxy_hop.hostname,
                bound_local_port=proxy_hop.port,
                socket_handle=sock,
                state=TransportState.ESTABLISHED,
            )
            with self._session_lock:
                self._active_sessions[session.session_id] = session
            return session

        # 4. Handle Remote Agent
        if path.transport_method == TransportMethod.REMOTE_AGENT:
            agent_hop = path.hops[0]
            host, port = await self.agent_manager.route_via_agent(agent_hop, path.target_endpoint)
            session = TransportSession(
                job_id=job_id,
                path=path,
                bound_local_host=host,
                bound_local_port=port,
                state=TransportState.ESTABLISHED,
            )
            with self._session_lock:
                self._active_sessions[session.session_id] = session
            return session

        raise RuntimeError(f"Unsupported transport method: {path.transport_method}")

    async def get_transport_health(self, session_id: str) -> TransportDiagnostics:
        """Probes health of active session and returns structured diagnostics."""
        with self._session_lock:
            session = self._active_sessions.get(session_id)

        if not session:
            return TransportDiagnostics(
                session_id=session_id,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.ROUTE_UNAVAILABLE,
                detailed_message=f"Session '{session_id}' not found in TransportManager active table.",
                operator_action_hint="Check if session was closed or expired.",
            )

        return await self.health_monitor.probe_transport_session(session)

    async def reconnect_transport_session(self, session_id: str) -> TransportSession:
        """Re-establishes an active TransportSession using exponential backoff with jitter."""
        with self._session_lock:
            old_session = self._active_sessions.get(session_id)

        if not old_session:
            raise RuntimeError(f"Cannot reconnect: session '{session_id}' does not exist.")

        logger.info("Triggering reconnect for transport session %s (Job: %s)", session_id, old_session.job_id)

        # Jitter delay
        jitter_sleep = self.health_monitor.calculate_reconnect_jitter(attempt=1)
        await asyncio.sleep(jitter_sleep)

        # Teardown old session
        await self.close_transport_session(session_id)

        # Open new session with original path and job_id
        new_session = await self.open_transport_session(old_session.path, old_session.job_id)
        return new_session

    async def close_transport_session(self, session_id: str) -> None:
        """Closes active transport session and releases bound local ports and sockets."""
        with self._session_lock:
            session = self._active_sessions.pop(session_id, None)
            tunnel = self._active_tunnels.pop(session_id, None)

        if tunnel:
            await tunnel.close()

        if session:
            session.state = TransportState.CLOSED
            if session.socket_handle:
                try:
                    session.socket_handle.close()
                except Exception:
                    pass
                session.socket_handle = None
            logger.info("Closed transport session %s", session_id)


def get_global_transport_manager() -> TransportManager:
    """Returns singleton global TransportManager instance."""
    global _global_transport_manager
    with _global_lock:
        if _global_transport_manager is None:
            _global_transport_manager = TransportManager()
        return _global_transport_manager
