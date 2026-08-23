"""
akaalEngine.discovery.core.cache
================================
Process-local TTL-governed discovery snapshot cache.
Keyed deterministically across endpoint fingerprint, scope, depth, sampling, options, and registry generation.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.snapshot import DiscoverySnapshot


class ProcessLocalDiscoveryCache:
    """
    Thread-safe, process-local in-memory cache for DiscoverySnapshot documents.
    Keyed by a complete composite identity of all material request parameters with strict TTL eviction.
    """

    def __init__(self, default_ttl_seconds: float = 300.0, max_entries: int = 128) -> None:
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries
        self._cache: dict[str, Tuple[DiscoverySnapshot, float]] = {}
        self._lock = threading.RLock()

    def generate_cache_key(
        self,
        endpoint_fingerprint: str,
        scope: DiscoveryScope,
        depth: DiscoveryDepth = DiscoveryDepth.STANDARD,
        allow_exact_counts: bool = False,
        sample_records: bool = False,
        sample_size: int = 100,
        max_sampled_tables: int = 10,
        max_objects: int = 50000,
        timeout_seconds: float = 60.0,
        registry_generation: Optional[int] = None,
        extra_options: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        Computes a deterministic composite cache key covering all material parameters.
        Prevents a QUICK snapshot from satisfying a DEEP or COMPLIANCE discovery request,
        and prevents truncated/limited snapshots from polluting full requests.
        """
        payload = {
            "endpoint_fp": endpoint_fingerprint,
            "scope": scope.to_dict(),
            "depth": depth.value,
            "allow_exact_counts": allow_exact_counts,
            "sample_records": sample_records,
            "sample_size": sample_size,
            "max_sampled_tables": max_sampled_tables,
            "max_objects": max_objects,
            "timeout_seconds": timeout_seconds,
            "registry_generation": registry_generation,
            "extra_options": dict(extra_options or {}),
        }
        raw_json = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        return f"{endpoint_fingerprint[:16]}:{depth.value}:{h[:24]}"

    def generate_key_from_context(
        self,
        endpoint_fingerprint: str,
        context: DiscoveryContext,
        registry_generation: Optional[int] = None,
    ) -> str:
        return self.generate_cache_key(
            endpoint_fingerprint=endpoint_fingerprint,
            scope=context.scope,
            depth=context.depth,
            allow_exact_counts=context.allow_exact_counts,
            sample_records=context.sample_records,
            sample_size=context.sample_size,
            max_sampled_tables=context.max_sampled_tables,
            max_objects=context.max_objects,
            timeout_seconds=context.timeout_seconds,
            registry_generation=registry_generation,
            extra_options=context.extra_options,
        )

    def get(self, cache_key: str) -> Optional[DiscoverySnapshot]:
        """Retrieves unexpired cached snapshot, or None on miss/expiry."""
        with self._lock:
            if cache_key not in self._cache:
                return None
            snapshot, expires_at = self._cache[cache_key]
            if time.time() > expires_at:
                del self._cache[cache_key]
                return None
            return snapshot

    def put(
        self,
        cache_key: str,
        snapshot: DiscoverySnapshot,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Stores a snapshot in cache with expiration."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            # Evict oldest if full
            if len(self._cache) >= self._max_entries:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[cache_key] = (snapshot, expires_at)

    def invalidate(self, cache_key: str) -> bool:
        """Invalidates a specific cache entry."""
        with self._lock:
            return self._cache.pop(cache_key, None) is not None

    def invalidate_all(self) -> int:
        """Clears all cached discovery snapshots."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count


default_discovery_cache = ProcessLocalDiscoveryCache()
