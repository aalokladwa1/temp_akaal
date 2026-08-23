"""
akaalEngine.connection.routing.dns
==================================
RFC 8305 Happy Eyeballs Dual-Stack DNS Resolver with microsecond timing and TTL caching.
Provides truthful DNS resolution facts and IP interleaving for resilient endpoint connection.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from typing import List, Optional, Tuple

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    DNSResolutionError,
    FailureCategory,
)
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.routing.dns")


class DNSResolutionResult:
    """Immutable result of DNS hostname resolution with measured timing."""

    def __init__(
        self,
        hostname: str,
        addresses: List[Tuple[int, str]],  # (socket.AF_INET / AF_INET6, ip_str)
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

    @property
    def primary_ip(self) -> Optional[str]:
        if self.addresses:
            return self.addresses[0][1]
        return None


class EnterpriseDNSResolver:
    """
    Enterprise RFC 8305 Happy Eyeballs dual-stack DNS resolver.
    """

    def __init__(self, cache_ttl_seconds: int = 60) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, DNSResolutionResult] = {}

    def resolve(self, hostname: str, force_refresh: bool = False) -> DNSResolutionResult:
        """
        Synchronously resolves a hostname to IPv4/IPv6 addresses with measured latency.
        """
        if not hostname or hostname in ("localhost", "127.0.0.1", "::1"):
            return DNSResolutionResult(
                hostname=hostname or "localhost",
                addresses=[(socket.AF_INET, "127.0.0.1")],
                cnames=[],
                dns_time_ms=0.1,
                ttl_seconds=3600,
            )

        # 1. Check IP literal
        try:
            socket.inet_pton(socket.AF_INET, hostname)
            return DNSResolutionResult(hostname, [(socket.AF_INET, hostname)], [], 0.0, 3600)
        except OSError:
            pass

        try:
            socket.inet_pton(socket.AF_INET6, hostname)
            return DNSResolutionResult(hostname, [(socket.AF_INET6, hostname)], [], 0.0, 3600)
        except OSError:
            pass

        # 2. Check Cache
        if not force_refresh and hostname in self._cache:
            res = self._cache[hostname]
            if not res.is_expired():
                return res

        # 3. Perform Socket Resolution with Timing
        t0 = time.perf_counter()
        try:
            addr_info = socket.getaddrinfo(
                hostname,
                None,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
                0,
                socket.AI_CANONNAME,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            addrs: list[tuple[int, str]] = []
            cnames: list[str] = []
            seen_ips = set()

            for family, socktype, proto, canonname, sockaddr in addr_info:
                if canonname and canonname not in cnames:
                    cnames.append(canonname)
                ip = sockaddr[0]
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    addrs.append((family, ip))

            # RFC 8305 interleaving: IPv6 first, followed by IPv4
            v6_addrs = [a for a in addrs if a[0] == socket.AF_INET6]
            v4_addrs = [a for a in addrs if a[0] == socket.AF_INET]
            interleaved: list[tuple[int, str]] = []
            for i in range(max(len(v6_addrs), len(v4_addrs))):
                if i < len(v6_addrs):
                    interleaved.append(v6_addrs[i])
                if i < len(v4_addrs):
                    interleaved.append(v4_addrs[i])

            result = DNSResolutionResult(
                hostname=hostname,
                addresses=interleaved or addrs,
                cnames=cnames,
                dns_time_ms=elapsed_ms,
                ttl_seconds=self.cache_ttl_seconds,
            )
            self._cache[hostname] = result
            return result

        except socket.gaierror as exc:
            msg = f"DNS resolution failed for hostname '{hostname}': {redact_text(str(exc))}"
            failure = ConnectionFailure(
                error_code="DNS_LOOKUP_FAILED",
                category=FailureCategory.DNS_FAILURE,
                message=msg,
                retryable=True,
                provider_id="dns",
                remediation="Verify hostname spelling, local DNS server health, or network route.",
            )
            raise DNSResolutionError(failure) from exc


# Global resolver instance
default_dns_resolver = EnterpriseDNSResolver()
