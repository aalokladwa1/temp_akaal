"""Multi-tier cache layer for Replication, Topology, Route, Health, and Checkpoints."""

import threading
from typing import Dict, Any, Optional


class ReplicationCache:
    """High-performance in-memory cache for replication data."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._topology_cache: Dict[str, Any] = {}
        self._route_cache: Dict[str, Any] = {}
        self._health_cache: Dict[str, Any] = {}
        self._checkpoint_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def get_topology(self, node_id: str) -> Optional[Any]:
        with self._lock:
            return self._topology_cache.get(node_id)

    def set_topology(self, node_id: str, data: Any) -> None:
        with self._lock:
            self._topology_cache[node_id] = data

    def get_route(self, route_key: str) -> Optional[Any]:
        with self._lock:
            return self._route_cache.get(route_key)

    def set_route(self, route_key: str, route_data: Any) -> None:
        with self._lock:
            self._route_cache[route_key] = route_data

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._topology_cache.clear()
            self._route_cache.clear()
            self._health_cache.clear()
            self._checkpoint_cache.clear()
