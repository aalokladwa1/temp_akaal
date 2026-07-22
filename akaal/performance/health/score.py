"""
Runtime Health Score Evaluator.
Calculates system metrics health.
"""

from typing import Dict, Any
from threading import RLock


class RuntimeHealthScore:
    """Continuously evaluates CPU, memory, network, storage, and worker health ratings."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._cpu_health = 1.0
        self._mem_health = 1.0
        self._storage_health = 1.0
        self._network_health = 1.0
        self._worker_health = 1.0
        self._opt_health = 1.0

    def update_metrics(self, cpu_util: float, memory_util: float, disk_latency_ms: float, net_latency_ms: float, active_workers: int, max_workers: int, rollbacks: int) -> None:
        with self._lock:
            # CPU Health: degrades if CPU utilization is above 85%
            self._cpu_health = 1.0 - (max(cpu_util - 85.0, 0.0) / 15.0) if cpu_util > 85.0 else 1.0
            self._cpu_health = max(min(self._cpu_health, 1.0), 0.0)

            # Memory Health: degrades if memory utilization is above 90%
            self._mem_health = 1.0 - (max(memory_util - 90.0, 0.0) / 10.0) if memory_util > 90.0 else 1.0
            self._mem_health = max(min(self._mem_health, 1.0), 0.0)

            # Storage Health: degrades if disk latency exceeds 50ms
            self._storage_health = 1.0 - (max(disk_latency_ms - 50.0, 0.0) / 100.0) if disk_latency_ms > 50.0 else 1.0
            self._storage_health = max(min(self._storage_health, 1.0), 0.0)

            # Network Health: degrades if network latency exceeds 100ms
            self._network_health = 1.0 - (max(net_latency_ms - 100.0, 0.0) / 200.0) if net_latency_ms > 100.0 else 1.0
            self._network_health = max(min(self._network_health, 1.0), 0.0)

            # Worker Health: degrades if workers are fully saturated
            worker_ratio = active_workers / max_workers if max_workers > 0 else 0.0
            self._worker_health = 1.0 - (max(worker_ratio - 0.9, 0.0) / 0.1) if worker_ratio > 0.9 else 1.0
            self._worker_health = max(min(self._worker_health, 1.0), 0.0)

            # Optimization Health: degrades by 20% per rollback event tracked
            self._opt_health = max(1.0 - (rollbacks * 0.20), 0.0)

    def calculate_overall_health(self) -> float:
        """Returns the weighted average overall score (0.0 to 100.0)."""
        with self._lock:
            weighted = (
                self._cpu_health * 0.25 +
                self._mem_health * 0.25 +
                self._storage_health * 0.15 +
                self._network_health * 0.15 +
                self._worker_health * 0.10 +
                self._opt_health * 0.10
            )
            return round(weighted * 100.0, 2)

    def get_detailed_scores(self) -> Dict[str, float]:
        with self._lock:
            return {
                "cpu_health": round(self._cpu_health * 100.0, 2),
                "memory_health": round(self._mem_health * 100.0, 2),
                "storage_health": round(self._storage_health * 100.0, 2),
                "network_health": round(self._network_health * 100.0, 2),
                "worker_health": round(self._worker_health * 100.0, 2),
                "optimization_health": round(self._opt_health * 100.0, 2),
                "overall_health": self.calculate_overall_health()
            }
