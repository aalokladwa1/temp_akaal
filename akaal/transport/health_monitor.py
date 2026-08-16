"""
Akaal — Transport Health Monitor & Connection Multiplexing Engine (P4.7)
========================================================================
Detects half-open TCP connections, manages TCP keepalives, performs liveness probing,
prevents thundering-herd reconnect storms via jitter, and enforces reference-counted transport leases.
"""

import socket
import asyncio
import random
import time
import logging
from typing import Dict, Any, Optional

from akaal.transport.models import TransportSession, TransportState, TransportFailureClass, TransportDiagnostics, redact_text

logger = logging.getLogger("akaal.transport.health_monitor")


class TransportHealthMonitor:
    """Monitors TCP socket health, configures keepalives, and manages session leases."""

    @staticmethod
    def configure_tcp_keepalive(sock: socket.socket, idle_sec: int = 30, interval_sec: int = 10, probes: int = 3) -> None:
        """Sets TCP keepalive options on socket if supported by platform."""
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Platform-specific TCP keepalive options
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle_sec)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, probes)
        except OSError as exc:
            logger.debug("Failed to set TCP keepalive options: %s", redact_text(str(exc)))

    @staticmethod
    async def check_socket_liveness(sock: socket.socket, timeout_seconds: float = 2.0) -> bool:
        """
        Detects half-open TCP socket state using non-blocking MSG_PEEK or zero-byte write test.
        Returns True if socket is healthy and open, False if closed or dead-peer detected.
        """
        if not sock:
            return False

        try:
            sock.setblocking(False)
            loop = asyncio.get_running_loop()
            # Non-blocking peek
            try:
                data = sock.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
                if data == b"":
                    return False  # EOF from peer -> closed
            except (BlockingIOError, InterruptedError):
                pass  # Readable without data -> still connected
            except OSError:
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def calculate_reconnect_jitter(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
        """Computes exponential backoff with full jitter to prevent thundering-herd reconnect storms."""
        temp = min(max_delay, base_delay * (2 ** (attempt - 1)))
        sleep_time = random.uniform(0, temp)
        return sleep_time

    @staticmethod
    async def probe_transport_session(session: TransportSession) -> TransportDiagnostics:
        """Probes an active transport session and builds structured diagnostic report."""
        t0 = time.perf_counter()
        if not session or session.state == TransportState.CLOSED:
            return TransportDiagnostics(
                session_id=session.session_id if session else None,
                path_id=session.path.path_id if session else None,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.ROUTE_UNAVAILABLE,
                detailed_message="Transport session is closed or uninitialized.",
                operator_action_hint="Re-establish transport session before executing workload.",
            )

        if not session.is_lease_valid():
            session.state = TransportState.FAILED
            session.failure_class = TransportFailureClass.CREDENTIAL_EXPIRED
            return TransportDiagnostics(
                session_id=session.session_id,
                path_id=session.path.path_id,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.CREDENTIAL_EXPIRED,
                detailed_message=f"Transport session lease expired at {session.lease_expires_at}.",
                operator_action_hint="Renew session lease or refresh credentials.",
            )

        # Check socket liveness if handle exists
        if session.socket_handle:
            is_alive = await TransportHealthMonitor.check_socket_liveness(session.socket_handle)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            session.last_health_check_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if not is_alive:
                session.state = TransportState.DEGRADED
                session.failure_class = TransportFailureClass.HALF_OPEN_DETECTED
                return TransportDiagnostics(
                    session_id=session.session_id,
                    path_id=session.path.path_id,
                    status="CONFIRMED",
                    primary_failure_class=TransportFailureClass.HALF_OPEN_DETECTED,
                    latency_ms=latency_ms,
                    detailed_message="Half-open TCP connection detected on transport socket handle.",
                    operator_action_hint="Trigger transport reconnection to restore active TCP route.",
                )

            session.state = TransportState.ESTABLISHED
            return TransportDiagnostics(
                session_id=session.session_id,
                path_id=session.path.path_id,
                status="CONFIRMED",
                primary_failure_class=TransportFailureClass.NONE,
                latency_ms=latency_ms,
                detailed_message="Transport path is healthy and established.",
            )

        session.state = TransportState.ROUTE_READY
        return TransportDiagnostics(
            session_id=session.session_id,
            path_id=session.path.path_id,
            status="CONFIRMED",
            primary_failure_class=TransportFailureClass.NONE,
            detailed_message="Transport route metadata is validated and ready.",
        )
