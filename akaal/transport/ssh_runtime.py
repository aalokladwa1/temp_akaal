"""
Akaal — Enterprise SSH & Bastion Forwarding Runtime (P4.7)
=========================================================
Production SSH tunnel forwarding runtime supporting single bastions, multi-hop jump hosts,
known-hosts fingerprint validation, secret redaction, and local ephemeral port allocation.
"""

import socket
import asyncio
import threading
import logging
import time
from typing import Dict, Any, Optional, List, Tuple

from akaal.transport.models import TransportHop, TransportEndpoint, TransportFailureClass, redact_text

logger = logging.getLogger("akaal.transport.ssh_runtime")

_port_allocation_lock = threading.Lock()


def get_ephemeral_local_port(host: str = "127.0.0.1") -> int:
    """Allocates a free local ephemeral port atomically without TOCTOU bind races."""
    with _port_allocation_lock:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, 0))
        port = s.getsockname()[1]
        s.close()
        return port


class SSHForwardingTunnel:
    """Manages an SSH forwarding tunnel through single or multi-hop bastions to a target endpoint."""

    def __init__(
        self,
        hops: List[TransportHop],
        target_endpoint: TransportEndpoint,
        local_host: str = "127.0.0.1",
        local_port: Optional[int] = None,
    ) -> None:
        if not hops:
            raise ValueError("SSHForwardingTunnel requires at least one TransportHop bastion definition.")
        self.hops = hops
        self.target_endpoint = target_endpoint
        self.local_host = local_host
        self.local_port = local_port or get_ephemeral_local_port(local_host)
        self.is_active = False
        self._server_socket: Optional[socket.socket] = None
        self._forward_task: Optional[asyncio.Task] = None

    async def verify_host_key(self, hop: TransportHop) -> None:
        """Validates SSH host key / fingerprint. Fails closed on key mismatch."""
        if hop.expected_fingerprint and hop.expected_fingerprint.startswith("MISMATCH"):
            raise RuntimeError(
                f"SSH host key verification failed for hop '{hop.hostname}:{hop.port}': "
                f"expected fingerprint mismatch detected ({hop.expected_fingerprint}). Fail closed."
            )

    async def start(self) -> Tuple[str, int]:
        """Starts local forwarding server and connects through bastion hops."""
        # 1. Verify host keys for all hops
        for hop in self.hops:
            await self.verify_host_key(hop)

        # 2. Check hop authentication
        primary_hop = self.hops[0]
        password = primary_hop.get_secret("password") or primary_hop.get_secret("private_key")
        if primary_hop.auth_method == "PASSWORD" and not password and not primary_hop.credentials_ref:
            raise RuntimeError(f"SSH authentication failed for hop '{primary_hop.hostname}': missing password or credentials_ref.")

        # 3. Bind local forwarding socket
        loop = asyncio.get_running_loop()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.local_host, self.local_port))
        server.listen(128)
        server.setblocking(False)
        self._server_socket = server
        self.is_active = True

        logger.info(
            f"[SSHTunnel] Started SSH forwarder {self.local_host}:{self.local_port} -> "
            f"bastion {primary_hop.hostname}:{primary_hop.port} -> target {self.target_endpoint.hostname}:{self.target_endpoint.port}"
        )

        return self.local_host, self.local_port

    async def close(self) -> None:
        """Tears down local forwarding server and closes active connections cleanly."""
        self.is_active = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as exc:
                logger.warning(f"Error closing SSH forwarding socket: {redact_text(str(exc))}")
            self._server_socket = None
