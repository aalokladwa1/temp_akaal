"""
Resource Governor for Platform 6.
Enforces hard limits on CPU usage, memory size, worker concurrency, and network bandwidth.
"""

from typing import Dict, Any
from threading import RLock

from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType


class ResourceGovernor:
    """Limits dynamic resource usages, raising exceptions if limits are violated."""

    def __init__(self, limits: Dict[str, Any] = None) -> None:
        self._lock = RLock()
        self._limits = limits or {
            "max_cpu_percent": 90.0,
            "max_ram_bytes": 1024 * 1024 * 1024 * 8,  # 8 GB
            "max_workers": 16,
            "max_network_mbps": 1000.0,
        }

    def update_limits(self, new_limits: Dict[str, Any]) -> None:
        with self._lock:
            self._limits.update(new_limits)

    def get_limits(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._limits)

    def enforce_cpu(self, requested_cpu: float) -> None:
        with self._lock:
            limit = self._limits.get("max_cpu_percent", 90.0)
            if requested_cpu > limit:
                raise PerformanceEngineError(
                    PerformanceFailureType.LIMIT_EXCEEDED,
                    f"Requested CPU allocation ({requested_cpu}%) exceeds governor limit ({limit}%)."
                )

    def enforce_ram(self, requested_ram_bytes: int) -> None:
        with self._lock:
            limit = self._limits.get("max_ram_bytes", 1024 * 1024 * 1024 * 8)
            if requested_ram_bytes > limit:
                raise PerformanceEngineError(
                    PerformanceFailureType.LIMIT_EXCEEDED,
                    f"Requested RAM allocation ({requested_ram_bytes / 1024 / 1024:.2f} MB) exceeds governor limit ({limit / 1024 / 1024:.2f} MB)."
                )

    def enforce_concurrency(self, requested_workers: int) -> None:
        with self._lock:
            limit = self._limits.get("max_workers", 16)
            if requested_workers > limit:
                raise PerformanceEngineError(
                    PerformanceFailureType.LIMIT_EXCEEDED,
                    f"Requested concurrency ({requested_workers} workers) exceeds governor limit ({limit} workers)."
                )
