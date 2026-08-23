"""
akaalEngine.runtime.resources.adaptive
======================================
Adaptive Concurrency Controller implementing AIMD (Additive Increase Multiplicative Decrease)
autoscale logic mined from legacy `akaal/performance/optimizers/adaptive_parallelism.py`.
"""

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AdaptiveAutoscaleDecision:
    current_workers: int
    recommended_workers: int
    is_scaling_event: bool
    scaling_direction: str  # "UP", "DOWN", "NONE"
    reason: str


class AdaptiveConcurrencyController:
    """
    AIMD Adaptive Concurrency Controller.
    Dynamically adjusts worker pool concurrency bounds based on execution metrics:
    CPU percent, memory utilization, queue backlog depth, and failure rates.
    """

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 32,
        target_cpu_pct: float = 75.0,
        target_memory_pct: float = 80.0,
    ) -> None:
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.target_cpu_pct = target_cpu_pct
        self.target_memory_pct = target_memory_pct
        self._current_workers = min_workers
        self._lock = RLock()

    @property
    def current_workers(self) -> int:
        with self._lock:
            return self._current_workers

    def evaluate(self, metrics: Dict[str, Any]) -> AdaptiveAutoscaleDecision:
        with self._lock:
            cpu = float(metrics.get("cpu_percent", 50.0))
            mem = float(metrics.get("memory_utilization_pct", 50.0))
            queue_depth = int(metrics.get("queue_depth", 0))
            worker_util = float(metrics.get("worker_utilization_pct", 70.0))

            direction = "NONE"
            reasons = []
            new_workers = self._current_workers

            # Multiplicative Decrease under high pressure
            if cpu > 88.0 or mem > 88.0:
                new_workers = max(self.min_workers, int(self._current_workers * 0.75))
                direction = "DOWN"
                if cpu > 88.0:
                    reasons.append(f"Elevated CPU load ({cpu:.1f}%)")
                if mem > 88.0:
                    reasons.append(f"Elevated RAM load ({mem:.1f}%)")

            # Additive Increase under capacity headroom + queue pressure
            elif cpu < self.target_cpu_pct and mem < self.target_memory_pct:
                if queue_depth > 10 or worker_util > 75.0:
                    new_workers = min(self.max_workers, self._current_workers + 1)
                    direction = "UP"
                    reasons.append(f"Available headroom (CPU {cpu:.1f}%, RAM {mem:.1f}%) with queue depth ({queue_depth})")

            if not reasons:
                reasons.append("Concurrency in steady state.")

            is_event = new_workers != self._current_workers
            if is_event:
                self._current_workers = new_workers

            return AdaptiveAutoscaleDecision(
                current_workers=self._current_workers,
                recommended_workers=new_workers,
                is_scaling_event=is_event,
                scaling_direction=direction,
                reason="; ".join(reasons),
            )
