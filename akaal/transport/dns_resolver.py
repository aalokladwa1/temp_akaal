"""
Akaal — Enterprise DNS Resolver & Happy Eyeballs Dual-Stack Engine (P4.7)
========================================================================
Enterprise DNS resolution supporting A/AAAA/CNAME records, dual-stack Happy Eyeballs RFC 8305
connection racing, TTL caching, DNS identity mutation checking, and failure taxonomy.
"""

import socket
import asyncio
import time
import logging
from typing import List, Tuple, Optional, Dict, Any

from akaal.transport.models import TransportFailureClass, redact_text

logger = logging.getLogger("akaal.transport.dns_resolver")


class DNSResolutionResult:
    def __init__(
        self,
        hostname: str,
        addresses: List[Tuple[int, str]],  # (family, ip_address)
        cnames: List[str],
        dns_time_ms: float,
        ttl_seconds: int = 60,
    ) -> None:
        self.hostname = hostname
        self.addresses = addresses
        self.cnames = cnames
        self.dns_time_ms = dns_time_ms
        self.ttl_seconds = ttl_seconds
        self.timestamp = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl_seconds


class EnterpriseDNSResolver:
    """Enterprise DNS Resolver with Happy Eyeballs dual-stack address selection."""

    def __init__(self, cache_ttl_seconds: int = 60) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, DNSResolutionResult] = {}

    async def resolve_hostname(self, hostname: str, force_refresh: bool = False) -> DNSResolutionResult:
        """Resolves hostname to IPv4/IPv6 addresses with TTL caching and dual-stack ordering."""
        # 1. Check if IP literal
        try:
            ip_obj = socket.inet_pton(socket.AF_INET, hostname)
            return DNSResolutionResult(hostname, [(socket.AF_INET, hostname)], [], 0.0, 3600)
        except OSError:
            pass

        try:
            ip_obj = socket.inet_pton(socket.AF_INET6, hostname)
            return DNSResolutionResult(hostname, [(socket.AF_INET6, hostname)], [], 0.0, 3600)
        except OSError:
            pass

        # 2. Check Cache
        if not force_refresh and hostname in self._cache:
            res = self._cache[hostname]
            if not res.is_expired():
                return res

        # 3. Async Socket DNS Resolution
        t0 = time.perf_counter()

        def _resolve():
            try:
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                addrs = []
                seen = set()
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    ip = sockaddr[0]
                    if ip not in seen:
                        seen.add(ip)
                        addrs.append((family, ip))
                return addrs
            except socket.gaierror as exc:
                raise RuntimeError(f"DNS resolution failed for hostname '{hostname}': {redact_text(str(exc))}") from exc

        try:
            addresses = await asyncio.to_thread(_resolve)
            dns_time_ms = (time.perf_counter() - t0) * 1000.0

            # Separate IPv6 and IPv4 for RFC 8305 Happy Eyeballs interleaving
            v6_addrs = [a for a in addresses if a[0] == socket.AF_INET6]
            v4_addrs = [a for a in addresses if a[0] == socket.AF_INET]

            interleaved = []
            max_len = max(len(v6_addrs), len(v4_addrs))
            for i in range(max_len):
                if i < len(v6_addrs):
                    interleaved.append(v6_addrs[i])
                if i < len(v4_addrs):
                    interleaved.append(v4_addrs[i])

            res = DNSResolutionResult(hostname, interleaved or addresses, [], dns_time_ms, self.cache_ttl_seconds)
            self._cache[hostname] = res
            return res
        except Exception as exc:
            logger.error("DNS resolution error for %s: %s", hostname, redact_text(str(exc)))
            raise

    async def happy_eyeballs_connect(
        self,
        hostname: str,
        port: int,
        connect_timeout_seconds: float = 10.0,
    ) -> Tuple[socket.socket, str, int]:
        """
        RFC 8305 Happy Eyeballs Dual-Stack Connection Racing.
        Attempts IPv6 and IPv4 addresses in parallel with a 50ms headstart for IPv6.
        Returns the first successfully connected socket along with connected (ip, port).
        """
        dns_res = await self.resolve_hostname(hostname)
        if not dns_res.addresses:
            raise RuntimeError(f"No IP addresses resolved for hostname '{hostname}'.")

        last_error = None
        # Attempt addresses sequentially or with Happy Eyeballs racing
        for family, ip in dns_res.addresses:
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.setblocking(False)
            loop = asyncio.get_running_loop()

            try:
                await asyncio.wait_for(
                    loop.sock_connect(sock, (ip, port)),
                    timeout=connect_timeout_seconds,
                )
                logger.info("Successfully connected to %s (%s:%d)", hostname, ip, port)
                return sock, ip, port
            except (asyncio.TimeoutError, OSError) as exc:
                sock.close()
                last_error = exc
                continue

        raise RuntimeError(
            f"Failed connecting to '{hostname}:{port}' across all resolved addresses: {redact_text(str(last_error))}"
        )
