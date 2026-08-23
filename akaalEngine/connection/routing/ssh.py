"""
akaalEngine.connection.routing.ssh
==================================
Authenticated SSH Bastion Tunnel Runtime with host-key verification and local port forwarding.
Enforces strict fail-closed security: requires real SSH authentication; never bypasses tunnel.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import RouteSpec
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    SSHTunnelError,
    DependencyMissingError,
)
from akaalEngine.connection.security.redaction import redact_text, SafeReprMixin
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer

logger = logging.getLogger("akaalEngine.connection.routing.ssh")


@dataclass
class SSHTunnelLease(SafeReprMixin):
    """
    Active local port forwarding lease through an authenticated SSH bastion.
    """
    tunnel_id: str
    ssh_host: str
    ssh_port: int
    local_bind_host: str
    local_bind_port: int
    remote_target_host: str
    remote_target_port: int
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    _client: Any = None
    _clients: list = field(default_factory=list)
    _server_socket: Optional[socket.socket] = None
    _forward_thread: Optional[threading.Thread] = None

    def close(self) -> None:
        """Closes local forwarded port listener and all chained SSH client connections."""
        self.is_active = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        for cli in reversed(self._clients):
            try:
                cli.close()
            except Exception:
                pass
        self._clients.clear()
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        logger.info(f"[SSHTunnelLease] Closed SSH tunnel lease '{self.tunnel_id}' (local port {self.local_bind_port})")


class SSHTunnelRuntime:
    """
    Establishes and manages authenticated SSH bastion tunnels.
    """

    def __init__(self, secret_consumer: Optional[SecretConsumer] = None) -> None:
        self.secret_consumer = secret_consumer or default_secret_consumer

    def establish_tunnel(
        self,
        route_spec: RouteSpec,
        target_host: str,
        target_port: int,
    ) -> SSHTunnelLease:
        """
        Establishes an authenticated SSH tunnel forwarding a local port to remote target_host:target_port.
        """
        if not route_spec.ssh_host:
            raise SSHTunnelError(
                ConnectionFailure(
                    error_code="SSH_HOST_NOT_SPECIFIED",
                    category=FailureCategory.SSH_FAILURE,
                    message="SSH bastion host was not specified in RouteSpec.",
                    retryable=False,
                    provider_id="ssh",
                )
            )

        # 1. Verify Paramiko library presence
        try:
            import paramiko
        except ImportError as exc:
            msg = "SSH bastion tunneling requires the 'paramiko' library. Install 'paramiko' or choose direct routing."
            failure = ConnectionFailure(
                error_code="SSH_DEPENDENCY_MISSING",
                category=FailureCategory.DEPENDENCY_MISSING,
                message=msg,
                retryable=False,
                provider_id="ssh",
                remediation="Run 'pip install paramiko' to enable SSH bastion routing.",
            )
            raise DependencyMissingError(failure) from exc

        # 2. Authenticate SSH Client
        resolved_secret = None
        try:
            ssh_client = paramiko.SSHClient()
            if route_spec.ssh_known_hosts_path:
                ssh_client.load_host_keys(route_spec.ssh_known_hosts_path)
                ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
            elif route_spec.ssh_host_key_fingerprint:
                # Custom missing host key policy verifying pinned fingerprint
                expected_fp = route_spec.ssh_host_key_fingerprint.lower().replace(":", "").strip()

                class PinnedFingerprintPolicy(paramiko.MissingHostKeyPolicy):
                    def missing_host_key(self, client: Any, hostname: str, key: Any) -> None:
                        import hashlib
                        raw_fp = hashlib.sha256(key.asbytes()).hexdigest().lower()
                        if raw_fp != expected_fp:
                            raise paramiko.SSHException(
                                f"SSH host key fingerprint mismatch for {hostname}: expected {expected_fp}, got {raw_fp}"
                            )

                ssh_client.set_missing_host_key_policy(PinnedFingerprintPolicy())
            elif route_spec.allow_unverified_ssh:
                logger.warning(
                    f"[SSHTunnelRuntime] PERMISSIVE_UNVERIFIED SSH host verification active for {route_spec.ssh_host}."
                )
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                msg = (
                    f"Strict SSH host verification failed for {route_spec.ssh_host}: "
                    f"Neither ssh_known_hosts_path nor ssh_host_key_fingerprint was provided. "
                    f"Set allow_unverified_ssh=True to explicitly permit unverified hosts in development."
                )
                failure = ConnectionFailure(
                    error_code="SSH_STRICT_HOST_VERIFICATION_FAILED",
                    category=FailureCategory.SSH_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id="ssh",
                    remediation="Provide ssh_known_hosts_path or ssh_host_key_fingerprint in RouteSpec.",
                )
                raise SSHTunnelError(failure)

            resolved_secrets = []
            password = None
            key_filename = None
            if route_spec.ssh_auth_spec:
                if route_spec.ssh_auth_spec.key_path:
                    key_filename = route_spec.ssh_auth_spec.key_path
                elif route_spec.ssh_auth_spec.secret_ref:
                    resolved_secret = self.secret_consumer.resolve(route_spec.ssh_auth_spec.secret_ref)
                    if resolved_secret:
                        resolved_secrets.append(resolved_secret)
                        password = resolved_secret.get_value()

            # Handle multi-hop jump hosts if specified in ssh_auth_spec.additional_params["jump_hosts"]
            jump_hosts = []
            if route_spec.ssh_auth_spec and isinstance(route_spec.ssh_auth_spec.additional_params, dict):
                jump_hosts = route_spec.ssh_auth_spec.additional_params.get("jump_hosts", [])

            active_clients = [ssh_client]
            current_transport = None

            ssh_client.connect(
                hostname=route_spec.ssh_host,
                port=route_spec.ssh_port,
                username=route_spec.ssh_user or "root",
                password=password,
                key_filename=key_filename,
                timeout=route_spec.connect_timeout_ms / 1000.0,
            )
            current_transport = ssh_client.get_transport()

            # Chain through intermediate jump hosts if provided
            for hop in jump_hosts:
                hop_host = hop.get("host") or hop.get("hostname")
                hop_port = hop.get("port", 22)
                hop_user = hop.get("user") or hop.get("username") or "root"
                hop_pass = None
                if hop.get("password"):
                    failure = ConnectionFailure(
                        error_code="PLAINTEXT_SECRET_PROHIBITED",
                        category=FailureCategory.INVALID_CONFIGURATION,
                        message=f"SSH jump host '{hop_host}' configured with plaintext password. Plaintext credentials are prohibited; use secret_ref.",
                        retryable=False,
                        provider_id="ssh",
                        remediation="Replace plaintext 'password' in jump_hosts configuration with a valid 'secret_ref' locator.",
                    )
                    raise SSHTunnelError(failure)
                elif hop.get("secret_ref"):
                    hop_secret = self.secret_consumer.resolve(hop["secret_ref"])
                    if hop_secret:
                        resolved_secrets.append(hop_secret)
                        hop_pass = hop_secret.get_value()
                else:
                    failure = ConnectionFailure(
                        error_code="SECRET_REFERENCE_REQUIRED",
                        category=FailureCategory.INVALID_CONFIGURATION,
                        message=f"SSH jump host '{hop_host}' missing secret_ref authentication parameter.",
                        retryable=False,
                        provider_id="ssh",
                        remediation="Specify a valid 'secret_ref' locator for each SSH jump host.",
                    )
                    raise SSHTunnelError(failure)

                if current_transport is None:
                    raise RuntimeError("Current SSH Transport is None when attempting jump host connection.")

                chan = current_transport.open_channel("direct-tcpip", (hop_host, hop_port), ("127.0.0.1", 0))
                hop_client = paramiko.SSHClient()

                # Apply host key policy to jump host
                hop_known_hosts = hop.get("known_hosts_path") or route_spec.ssh_known_hosts_path
                hop_fp = hop.get("host_key_fingerprint") or route_spec.ssh_host_key_fingerprint

                if hop_known_hosts:
                    hop_client.load_host_keys(hop_known_hosts)
                    hop_client.set_missing_host_key_policy(paramiko.RejectPolicy())
                elif hop_fp:
                    expected_hop_fp = hop_fp.lower().replace(":", "").strip()

                    class HopPinnedFingerprintPolicy(paramiko.MissingHostKeyPolicy):
                        def missing_host_key(self, client: Any, hostname: str, key: Any) -> None:
                            import hashlib
                            raw_fp = hashlib.sha256(key.asbytes()).hexdigest().lower()
                            if raw_fp != expected_hop_fp:
                                raise paramiko.SSHException(
                                    f"SSH host key fingerprint mismatch for jump host {hostname}: expected {expected_hop_fp}, got {raw_fp}"
                                )

                    hop_client.set_missing_host_key_policy(HopPinnedFingerprintPolicy())
                elif route_spec.allow_unverified_ssh:
                    hop_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                else:
                    hop_client.set_missing_host_key_policy(paramiko.RejectPolicy())

                hop_client.connect(
                    hostname=hop_host,
                    port=hop_port,
                    username=hop_user,
                    password=hop_pass,
                    sock=chan,
                    timeout=route_spec.connect_timeout_ms / 1000.0,
                )
                active_clients.append(hop_client)
                current_transport = hop_client.get_transport()

            # 3. Find an available local port
            local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_sock.bind(("127.0.0.1", 0))
            local_port = local_sock.getsockname()[1]
            local_sock.listen(5)

            transport = current_transport
            if transport is None:
                raise RuntimeError("SSH Transport is None after successful connect.")

            tunnel_lease = SSHTunnelLease(
                tunnel_id=f"ssh-{route_spec.ssh_host}:{local_port}",
                ssh_host=route_spec.ssh_host,
                ssh_port=route_spec.ssh_port,
                local_bind_host="127.0.0.1",
                local_bind_port=local_port,
                remote_target_host=target_host,
                remote_target_port=target_port,
                is_active=True,
                _clients=active_clients,
                _client=active_clients[-1],
                _server_socket=local_sock,
            )

            # Forwarding worker loop in background thread
            def _forward_handler(server_s, trans, rem_host, rem_port, lease):
                while lease.is_active:
                    try:
                        client_s, _ = server_s.accept()
                        chan = trans.open_channel("direct-tcpip", (rem_host, rem_port), client_s.getpeername())
                        if chan is None:
                            client_s.close()
                            continue

                        def _pipe(src, dst):
                            try:
                                while True:
                                    data = src.recv(4096)
                                    if not data:
                                        break
                                    dst.sendall(data)
                            except Exception:
                                pass
                            finally:
                                try:
                                    src.close()
                                except Exception:
                                    pass
                                try:
                                    dst.close()
                                except Exception:
                                    pass

                        t1 = threading.Thread(target=_pipe, args=(client_s, chan), daemon=True)
                        t2 = threading.Thread(target=_pipe, args=(chan, client_s), daemon=True)
                        t1.start()
                        t2.start()
                    except Exception:
                        break

            f_thread = threading.Thread(
                target=_forward_handler,
                args=(local_sock, transport, target_host, target_port, tunnel_lease),
                daemon=True,
            )
            tunnel_lease._forward_thread = f_thread
            f_thread.start()

            logger.info(
                f"[SSHTunnelRuntime] SSH Tunnel established: 127.0.0.1:{local_port} -> {route_spec.ssh_host} -> {target_host}:{target_port}"
            )
            return tunnel_lease

        except Exception as exc:
            # Clean up all opened clients on failure
            if 'active_clients' in locals():
                for cli in reversed(active_clients):
                    try:
                        cli.close()
                    except Exception:
                        pass
                active_clients.clear()

            if isinstance(exc, (DependencyMissingError, SSHTunnelError)):
                raise
            msg = f"Failed to establish SSH bastion connection to {route_spec.ssh_host}:{route_spec.ssh_port}: {redact_text(str(exc))}"
            failure = ConnectionFailure(
                error_code="SSH_AUTHENTICATION_FAILED",
                category=FailureCategory.SSH_FAILURE,
                message=msg,
                retryable=False,
                provider_id="ssh",
                remediation="Verify SSH bastion host, port, username, credentials, host keys, and firewall rules.",
            )
            raise SSHTunnelError(failure) from exc
        finally:
            if 'resolved_secrets' in locals():
                for s in resolved_secrets:
                    try:
                        s.wipe()
                    except Exception:
                        pass
