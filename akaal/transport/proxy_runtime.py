"""
Akaal — Enterprise Proxy Runtime Engine (P4.7)
==============================================
Production HTTP CONNECT and SOCKS5 proxy runtime engine supporting remote DNS resolution,
proxy authentication, secret redaction, and deterministic failure classification.
"""

import socket
import asyncio
import logging
import struct
from typing import Tuple, Optional

from akaal.transport.models import TransportHop, TransportEndpoint, TransportFailureClass, redact_text

logger = logging.getLogger("akaal.transport.proxy_runtime")


class EnterpriseProxyRuntime:
    """Manages HTTP CONNECT and SOCKS5 proxy connection negotiation."""

    @staticmethod
    async def connect_via_http_connect(
        proxy_hop: TransportHop,
        target_endpoint: TransportEndpoint,
        connect_timeout_seconds: float = 10.0,
    ) -> socket.socket:
        """Establishes TCP connection to target endpoint via HTTP CONNECT proxy."""
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)

        # 1. Connect to proxy host
        try:
            await asyncio.wait_for(
                loop.sock_connect(sock, (proxy_hop.hostname, proxy_hop.port)),
                timeout=connect_timeout_seconds,
            )
        except Exception as exc:
            sock.close()
            raise RuntimeError(f"HTTP Proxy at '{proxy_hop.hostname}:{proxy_hop.port}' is unavailable: {redact_text(str(exc))}") from exc

        # 2. Prepare HTTP CONNECT request
        connect_req = f"CONNECT {target_endpoint.hostname}:{target_endpoint.port} HTTP/1.1\r\nHost: {target_endpoint.hostname}:{target_endpoint.port}\r\n"
        username = proxy_hop.username
        password = proxy_hop.get_secret("password")
        if username and password:
            import base64
            auth_bytes = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            connect_req += f"Proxy-Authorization: Basic {auth_bytes}\r\n"
        connect_req += "\r\n"

        # 3. Send CONNECT request and parse response
        try:
            await loop.sock_sendall(sock, connect_req.encode("utf-8"))
            resp_bytes = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=connect_timeout_seconds)
            resp_str = resp_bytes.decode("utf-8", errors="replace")

            if "200" not in resp_str.split("\r\n")[0]:
                sock.close()
                if "407" in resp_str:
                    raise RuntimeError("HTTP Proxy authentication failed (407 Proxy Authentication Required).")
                raise RuntimeError(f"HTTP Proxy rejected CONNECT route to '{target_endpoint.hostname}:{target_endpoint.port}': {resp_str.splitlines()[0]}")

            logger.info("HTTP CONNECT tunnel established through proxy %s to target %s:%d", proxy_hop.hostname, target_endpoint.hostname, target_endpoint.port)
            return sock
        except Exception as exc:
            sock.close()
            raise RuntimeError(f"HTTP Proxy negotiation failed: {redact_text(str(exc))}") from exc

    @staticmethod
    async def connect_via_socks5(
        proxy_hop: TransportHop,
        target_endpoint: TransportEndpoint,
        connect_timeout_seconds: float = 10.0,
    ) -> socket.socket:
        """Establishes TCP connection to target endpoint via SOCKS5 proxy with remote DNS resolution."""
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)

        try:
            await asyncio.wait_for(
                loop.sock_connect(sock, (proxy_hop.hostname, proxy_hop.port)),
                timeout=connect_timeout_seconds,
            )
        except Exception as exc:
            sock.close()
            raise RuntimeError(f"SOCKS5 Proxy at '{proxy_hop.hostname}:{proxy_hop.port}' is unavailable: {redact_text(str(exc))}") from exc

        try:
            # 1. Greeting (NO AUTH or USER/PASS)
            username = proxy_hop.username
            password = proxy_hop.get_secret("password")
            if username and password:
                await loop.sock_sendall(sock, b"\x05\x02\x00\x02")  # Methods: NO AUTH (0), USER/PASS (2)
            else:
                await loop.sock_sendall(sock, b"\x05\x01\x00")

            greet_resp = await asyncio.wait_for(loop.sock_recv(sock, 2), timeout=connect_timeout_seconds)
            if len(greet_resp) < 2 or greet_resp[0] != 5:
                sock.close()
                raise RuntimeError("Invalid SOCKS5 proxy protocol response.")

            method = greet_resp[1]
            if method == 2 and username and password:
                # Subnegotiation
                auth_req = b"\x01" + bytes([len(username)]) + username.encode("utf-8") + bytes([len(password)]) + password.encode("utf-8")
                await loop.sock_sendall(sock, auth_req)
                auth_resp = await asyncio.wait_for(loop.sock_recv(sock, 2), timeout=connect_timeout_seconds)
                if len(auth_resp) < 2 or auth_resp[1] != 0:
                    sock.close()
                    raise RuntimeError("SOCKS5 Proxy authentication failed.")
            elif method == 255:
                sock.close()
                raise RuntimeError("SOCKS5 Proxy requires authentication method not supported by client.")

            # 2. Connect Command with Remote Domain Name Resolution (ATYP 0x03)
            host_bytes = target_endpoint.hostname.encode("utf-8")
            req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack("!H", target_endpoint.port)
            await loop.sock_sendall(sock, req)

            conn_resp = await asyncio.wait_for(loop.sock_recv(sock, 512), timeout=connect_timeout_seconds)
            if len(conn_resp) < 4 or conn_resp[1] != 0:
                sock.close()
                err_code = conn_resp[1] if len(conn_resp) > 1 else 99
                raise RuntimeError(f"SOCKS5 Proxy route connection rejected with status code {err_code}.")

            logger.info("SOCKS5 tunnel established through proxy %s to target %s:%d", proxy_hop.hostname, target_endpoint.hostname, target_endpoint.port)
            return sock
        except Exception as exc:
            sock.close()
            raise RuntimeError(f"SOCKS5 Proxy negotiation failed: {redact_text(str(exc))}") from exc
