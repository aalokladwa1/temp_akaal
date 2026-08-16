"""
Akaal — Enterprise Proxy Runtime Engine (P4.7)
==============================================
Production HTTP CONNECT and SOCKS5 proxy runtime engine supporting remote DNS resolution,
proxy authentication, header buffer accumulation, exact frame reading, and secret redaction.
"""

import socket
import asyncio
import logging
import struct
from typing import Tuple, Optional

from akaal.transport.models import TransportHop, TransportEndpoint, TransportFailureClass, redact_text

logger = logging.getLogger("akaal.transport.proxy_runtime")


async def _recv_exact(loop: asyncio.AbstractEventLoop, sock: socket.socket, num_bytes: int, timeout: float) -> bytes:
    """Reads exactly num_bytes from a non-blocking socket within timeout."""
    buf = bytearray()
    t_end = asyncio.get_running_loop().time() + timeout
    while len(buf) < num_bytes:
        rem_timeout = t_end - asyncio.get_running_loop().time()
        if rem_timeout <= 0:
            raise asyncio.TimeoutError(f"Timed out reading {num_bytes} bytes from proxy socket.")
        chunk = await asyncio.wait_for(loop.sock_recv(sock, num_bytes - len(buf)), timeout=rem_timeout)
        if not chunk:
            raise ConnectionResetError("Proxy socket closed prematurely before frame completion.")
        buf.extend(chunk)
    return bytes(buf)


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

        # 3. Send CONNECT request and parse response until \r\n\r\n header delimiter (bounded max 64KB)
        try:
            await loop.sock_sendall(sock, connect_req.encode("utf-8"))
            buffer = bytearray()
            max_headers = 65536
            t_end = loop.time() + connect_timeout_seconds

            while b"\r\n\r\n" not in buffer and len(buffer) < max_headers:
                rem = t_end - loop.time()
                if rem <= 0:
                    raise asyncio.TimeoutError("HTTP Proxy CONNECT response header timeout.")
                chunk = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=rem)
                if not chunk:
                    raise ConnectionResetError("HTTP Proxy closed connection during header negotiation.")
                buffer.extend(chunk)

            resp_str = buffer.decode("utf-8", errors="replace")
            status_line = resp_str.split("\r\n")[0] if resp_str else ""

            if "200" not in status_line:
                sock.close()
                if "407" in resp_str:
                    raise RuntimeError("HTTP Proxy authentication failed (407 Proxy Authentication Required).")
                raise RuntimeError(f"HTTP Proxy rejected CONNECT route to '{target_endpoint.hostname}:{target_endpoint.port}': {status_line}")

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

            greet_resp = await _recv_exact(loop, sock, 2, connect_timeout_seconds)
            if len(greet_resp) < 2 or greet_resp[0] != 5:
                sock.close()
                raise RuntimeError("Invalid SOCKS5 proxy protocol response.")

            method = greet_resp[1]
            if method == 2 and username and password:
                # Subnegotiation
                auth_req = b"\x01" + bytes([len(username)]) + username.encode("utf-8") + bytes([len(password)]) + password.encode("utf-8")
                await loop.sock_sendall(sock, auth_req)
                auth_resp = await _recv_exact(loop, sock, 2, connect_timeout_seconds)
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

            # SOCKS5 server header response (4 bytes minimum: VER, REP, RSV, ATYP)
            header = await _recv_exact(loop, sock, 4, connect_timeout_seconds)
            if header[1] != 0:
                sock.close()
                raise RuntimeError(f"SOCKS5 Proxy route connection rejected with status code {header[1]}.")

            atyp = header[3]
            if atyp == 1:
                await _recv_exact(loop, sock, 4 + 2, connect_timeout_seconds)  # IPv4 + Port
            elif atyp == 3:
                domain_len_bytes = await _recv_exact(loop, sock, 1, connect_timeout_seconds)
                domain_len = domain_len_bytes[0]
                await _recv_exact(loop, sock, domain_len + 2, connect_timeout_seconds)  # Domain + Port
            elif atyp == 4:
                await _recv_exact(loop, sock, 16 + 2, connect_timeout_seconds)  # IPv6 + Port

            logger.info("SOCKS5 tunnel established through proxy %s to target %s:%d", proxy_hop.hostname, target_endpoint.hostname, target_endpoint.port)
            return sock
        except Exception as exc:
            sock.close()
            raise RuntimeError(f"SOCKS5 Proxy negotiation failed: {redact_text(str(exc))}") from exc
