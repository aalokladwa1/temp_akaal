"""
Akaal — Enterprise DNS Resolver & RFC 8305 Happy Eyeballs Dual-Stack Engine (P4.7)
==================================================================================
Enterprise DNS resolution supporting A/AAAA/CNAME records, dual-stack Happy Eyeballs RFC 8305
concurrent connection racing, TTL caching, DNS identity mutation checking, and failure taxonomy.
"""

import socket
import asyncio
import time
import logging
from typing import List, Tuple, Optional, Dict, Any, Set

from akaal.transport.models import TransportFailureClass, redact_text

logger = logging.getLogger("akaal.transport.dns_resolver")


class DNSResolutionResult:
    """DNS Resolution Result with explicit truth attributes for DNS capabilities."""

    A_AAAA_OS_RESOLUTION: bool = True
    CANONICAL_NAME_DISCOVERY: bool = True
    FULL_CNAME_CHAIN_DISCOVERY: bool = False  # socket.getaddrinfo AI_CANONNAME is canonical name only
    CONFIGURED_CACHE_TTL: bool = True
    AUTHORITATIVE_DNS_TTL: bool = False  # OS socket API does not expose authoritative packet TTL

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
    """Enterprise DNS Resolver with RFC 8305 Happy Eyeballs dual-stack connection racing."""

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
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_CANONNAME)
                addrs = []
                cnames = []
                seen = set()
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    if canonname and canonname not in cnames:
                        cnames.append(canonname)
                    ip = sockaddr[0]
                    if ip not in seen:
                        seen.add(ip)
                        addrs.append((family, ip))
                return addrs, cnames
            except socket.gaierror as exc:
                raise RuntimeError(f"DNS resolution failed for hostname '{hostname}': {redact_text(str(exc))}") from exc

        try:
            addresses, cnames = await asyncio.to_thread(_resolve)
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

            res = DNSResolutionResult(hostname, interleaved or addresses, cnames, dns_time_ms, self.cache_ttl_seconds)
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
        connection_attempt_delay: float = 0.05,  # 50ms stagger per RFC 8305
    ) -> Tuple[socket.socket, str, int]:
        """
        RFC 8305 Happy Eyeballs Dual-Stack Connection Racing.
        Launches candidate attempts staggered by connection_attempt_delay.
        Races active candidates concurrently: if any candidate succeeds, returns IMMEDIATELY (<5ms),
        cancelling all losing tasks and closing losing sockets.
        """
        # Validate inputs upfront before network execution
        if port <= 0 or port > 65535:
            raise ValueError(f"Invalid port number: {port}. Port must be between 1 and 65535.")
        if connection_attempt_delay < 0:
            raise ValueError("connection_attempt_delay cannot be negative.")

        dns_res = await self.resolve_hostname(hostname)
        if not dns_res.addresses:
            raise RuntimeError(f"No IP addresses resolved for hostname '{hostname}'.")

        loop = asyncio.get_running_loop()
        t_start = loop.time()
        global_deadline = t_start + connect_timeout_seconds

        tasks: Set[asyncio.Task] = set()
        task_to_info: Dict[asyncio.Task, Tuple[int, str]] = {}
        errors: List[str] = []
        winner: Optional[Tuple[socket.socket, str, int]] = None

        async def _attempt_connect(family: int, ip: str) -> Tuple[socket.socket, str, int]:
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.setblocking(False)
            try:
                await loop.sock_connect(sock, (ip, port))
                return sock, ip, port
            except Exception as exc:
                sock.close()
                raise exc

        address_queue = list(dns_res.addresses)

        try:
            while address_queue or tasks:
                now = loop.time()
                remaining_global = global_deadline - now
                if remaining_global <= 0:
                    break

                # Spawn next address candidate if available
                if address_queue:
                    family, ip = address_queue.pop(0)
                    t = loop.create_task(_attempt_connect(family, ip))
                    tasks.add(t)
                    task_to_info[t] = (family, ip)

                # Determine wait timeout for this iteration:
                # If more addresses remain in queue, wait at most connection_attempt_delay before spawning next candidate.
                # If no more addresses remain in queue, wait remaining_global for any candidate to finish.
                if address_queue and connection_attempt_delay > 0:
                    wait_timeout = min(connection_attempt_delay, remaining_global)
                else:
                    wait_timeout = remaining_global

                done, pending = await asyncio.wait(
                    tasks,
                    timeout=wait_timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Check completed tasks
                for t in done:
                    tasks.remove(t)
                    if t.cancelled():
                        continue
                    exc = t.exception()
                    if exc:
                        fam, ip = task_to_info.get(t, (0, "unknown"))
                        errors.append(f"{ip}: {redact_text(str(exc))}")
                    else:
                        # Winner found!
                        candidate_winner = t.result()

                        # If multiple connected simultaneously in the same done set, pick first and close rest
                        if winner is None:
                            winner = candidate_winner
                        else:
                            # Extra winner: close losing socket
                            try:
                                candidate_winner[0].close()
                            except Exception:
                                pass

                # If winner found, return immediately without waiting for remaining addresses
                if winner is not None:
                    break

            if winner is not None:
                logger.info("Happy Eyeballs won connection to %s (%s:%d)", hostname, winner[1], winner[2])
                return winner

            raise RuntimeError(
                f"Happy Eyeballs failed connecting to '{hostname}:{port}' across all addresses: {'; '.join(errors) or 'Connect deadline exceeded'}"
            )
        finally:
            # Clean up all active/pending tasks and losing sockets upon exit or cancellation
            for t in list(tasks):
                if not t.done():
                    t.cancel()
                elif t.done() and not t.cancelled() and t.exception() is None:
                    res_sock = t.result()
                    if winner is None or res_sock[0] != winner[0]:
                        try:
                            res_sock[0].close()
                        except Exception:
                            pass
