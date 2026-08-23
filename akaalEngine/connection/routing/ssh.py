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
    _server_socket: Optional[socket.socket] = None
    _forward_thread: Optional[threading.Thread] = None

    def close(self) -> None:
        """Closes local forwarded port listener and SSH client connection."""
        self.is_active = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
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

            password = None
            key_filename = None
            if route_spec.ssh_auth_spec:
                if route_spec.ssh_auth_spec.key_path:
                    key_filename = route_spec.ssh_auth_spec.key_path
                elif route_spec.ssh_auth_spec.secret_ref:
                    resolved_secret = self.secret_consumer.resolve(route_spec.ssh_auth_spec.secret_ref)
                    if resolved_secret:
                        password = resolved_secret.get_value()

            ssh_client.connect(
                hostname=route_spec.ssh_host,
                port=route_spec.ssh_port,
                username=route_spec.ssh_user or "root",
                password=password,
                key_filename=key_filename,
                timeout=route_spec.connect_timeout_ms / 1000.0,
            )

            # 3. Find an available local port
            local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_sock.bind(("127.0.0.1", 0))
            local_port = local_sock.getsockname()[1]
            local_sock.listen(5)

            transport = ssh_client.get_transport()
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
                _client=ssh_client,
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
            if resolved_secret is not None:
                resolved_secret.wipe()
