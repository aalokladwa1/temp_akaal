"""
akaalEngine.connection.routing.proxy
====================================
HTTP and SOCKS Proxy routing, CONNECT tunneling, local port forwarding leases, and socket traversal.
Truthful architecture: physically routes traffic via HTTP CONNECT local port forwarding leases;
explicitly fails closed on unconfigured or unsupported proxy modes (e.g. SOCKS).
"""

from __future__ import annotations

import base64
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import RouteSpec, RouteType
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    RouteResolutionError,
)
from akaalEngine.connection.security.redaction import redact_text, SafeReprMixin
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer

logger = logging.getLogger("akaalEngine.connection.routing.proxy")


@dataclass
class ProxyTunnelLease(SafeReprMixin):
    """
    Active local port forwarding lease through an HTTP CONNECT proxy tunnel.
    Binds provider drivers to a local forwarded socket bridging through the proxy.
    """
    tunnel_id: str
    proxy_host: str
    proxy_port: int
    local_bind_host: str
    local_bind_port: int
    remote_target_host: str
    remote_target_port: int
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    _server_socket: Optional[socket.socket] = None
    _forward_thread: Optional[threading.Thread] = None

    def close(self) -> None:
        """Closes local forwarded listener socket and deactivates tunnel lease."""
        self.is_active = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        logger.info(f"[ProxyTunnelLease] Closed proxy tunnel lease '{self.tunnel_id}' (local port {self.local_bind_port})")


class ProxyTunnel:
    """Manages socket-level proxy negotiation (HTTP CONNECT) and local forwarding leases."""

    def __init__(self, secret_consumer: Optional[SecretConsumer] = None) -> None:
        self.secret_consumer = secret_consumer or default_secret_consumer

    def open_http_connect_tunnel(
        self,
        proxy_host: str,
        proxy_port: int,
        target_host: str,
        target_port: int,
        timeout_seconds: float = 15.0,
        auth_spec: Optional[Any] = None,
    ) -> socket.socket:
        """
        Connects to an HTTP proxy server and issues a CONNECT command to establish a bidirectional TCP stream.
        Wipes resolved authentication material in a finally block.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_seconds)
        resolved_secret = None
        try:
            sock.connect((proxy_host, proxy_port))

            headers = [
                f"CONNECT {target_host}:{target_port} HTTP/1.1",
                f"Host: {target_host}:{target_port}",
                "User-Agent: akaalEngine/1.0",
                "Proxy-Connection: Keep-Alive",
            ]

            if auth_spec and getattr(auth_spec, "username", None):
                pwd = ""
                secret_ref = getattr(auth_spec, "secret_ref", None)
                if secret_ref:
                    resolved_secret = self.secret_consumer.resolve(secret_ref)
                    if resolved_secret:
                        pwd = resolved_secret.get_value()
                creds = f"{auth_spec.username}:{pwd}"
                b64_creds = base64.b64encode(creds.encode("utf-8")).decode("ascii")
                headers.append(f"Proxy-Authorization: Basic {b64_creds}")

            connect_req = "\r\n".join(headers) + "\r\n\r\n"
            sock.sendall(connect_req.encode("ascii"))

            # Read HTTP response status
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                resp += chunk

            first_line = resp.split(b"\r\n")[0].decode("ascii", errors="replace")
            if "200" not in first_line:
                sock.close()
                msg = f"HTTP Proxy refused connection to {target_host}:{target_port}: {first_line}"
                failure = ConnectionFailure(
                    error_code="PROXY_CONNECT_REFUSED",
                    category=FailureCategory.PROXY_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id="proxy",
                    remediation="Verify proxy credentials, firewall rules, and target port allowlist.",
                )
                raise RouteResolutionError(failure)

            return sock

        except Exception as exc:
            sock.close()
            if isinstance(exc, RouteResolutionError):
                raise
            msg = f"Failed to establish HTTP proxy tunnel via {proxy_host}:{proxy_port}: {redact_text(str(exc))}"
            failure = ConnectionFailure(
                error_code="PROXY_TUNNEL_FAILED",
                category=FailureCategory.PROXY_FAILURE,
                message=msg,
                retryable=True,
                provider_id="proxy",
            )
            raise RouteResolutionError(failure) from exc
        finally:
            if resolved_secret is not None:
                resolved_secret.wipe()

    def establish_http_connect_tunnel(
        self,
        route_spec: RouteSpec,
        target_host: str,
        target_port: int,
    ) -> ProxyTunnelLease:
        """
        Establishes a local port forwarding lease that routes all incoming TCP connections
        through an authenticated HTTP CONNECT tunnel to the target host and port.
        """
        if not route_spec.proxy_host or not route_spec.proxy_port:
            failure = ConnectionFailure(
                error_code="PROXY_HOST_PORT_REQUIRED",
                category=FailureCategory.PROXY_FAILURE,
                message="HTTP Proxy routing requires proxy_host and proxy_port in RouteSpec.",
                retryable=False,
                provider_id="proxy",
            )
            raise RouteResolutionError(failure)

        # 1. Bind local forwarding listener
        local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local_sock.bind(("127.0.0.1", 0))
        local_port = local_sock.getsockname()[1]
        local_sock.listen(5)

        tunnel_lease = ProxyTunnelLease(
            tunnel_id=f"proxy-http-{route_spec.proxy_host}:{local_port}",
            proxy_host=route_spec.proxy_host,
            proxy_port=route_spec.proxy_port,
            local_bind_host="127.0.0.1",
            local_bind_port=local_port,
            remote_target_host=target_host,
            remote_target_port=target_port,
            is_active=True,
            _server_socket=local_sock,
        )

        # 2. Background forwarding worker loop
        def _forward_loop(server_s: socket.socket, lease: ProxyTunnelLease, spec: RouteSpec, rem_h: str, rem_p: int):
            while lease.is_active:
                try:
                    client_s, _ = server_s.accept()
                    # Open proxy tunnel
                    try:
                        proxy_sock = self.open_http_connect_tunnel(
                            proxy_host=spec.proxy_host or "",
                            proxy_port=spec.proxy_port or 0,
                            target_host=rem_h,
                            target_port=rem_p,
                            timeout_seconds=spec.connect_timeout_ms / 1000.0,
                            auth_spec=spec.proxy_auth_spec,
                        )
                    except Exception as e:
                        logger.error(f"[ProxyTunnel] Error opening CONNECT tunnel: {e}")
                        client_s.close()
                        continue

                    def _pipe(src: socket.socket, dst: socket.socket):
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

                    t1 = threading.Thread(target=_pipe, args=(client_s, proxy_sock), daemon=True)
                    t2 = threading.Thread(target=_pipe, args=(proxy_sock, client_s), daemon=True)
                    t1.start()
                    t2.start()
                except Exception:
                    break

        f_thread = threading.Thread(
            target=_forward_loop,
            args=(local_sock, tunnel_lease, route_spec, target_host, target_port),
            daemon=True,
        )
        tunnel_lease._forward_thread = f_thread
        f_thread.start()

        logger.info(
            f"[ProxyTunnel] HTTP Proxy tunnel established: 127.0.0.1:{local_port} -> {route_spec.proxy_host}:{route_spec.proxy_port} -> {target_host}:{target_port}"
        )
        return tunnel_lease

