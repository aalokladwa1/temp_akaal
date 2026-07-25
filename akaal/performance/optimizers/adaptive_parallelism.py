"""
AKAAL Platform — Adaptive Parallelism Engine.
=============================================
Extends ParallelExecutionManager and composes ParallelismAnalyzer to dynamically autoscale worker pool count.
Reuses shared runtime telemetry signals (CPU, RAM, connection pool, lock contention, worker utilization, queue depth).
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from threading import RLock

from akaal.performance.optimizers.parallel import ParallelExecutionManager
from akaal.planner.analyzers.parallelism_analyzer import ParallelismAnalyzer


@dataclass
class ParallelismAutoscaleDecision:
    current_workers: int
    recommended_workers: int
    parallel_chunks: int
    is_scaling_event: bool
    scaling_direction: str  # "UP", "DOWN", "NONE"
    reason: str


class AdaptiveParallelismEngine(ParallelExecutionManager):
    """
    Enterprise Adaptive Parallelism Engine.
    Dynamically scales extraction/loader worker concurrency based on multi-dimensional telemetry:
    CPU, RAM, Connection Pool Utilization, Database Lock Contention, Worker Utilization, and Queue Backlog.
    """

    def __init__(self, parallelism_analyzer: Optional[ParallelismAnalyzer] = None) -> None:
        super().__init__()
        self.version = "2.0.0"
        self._lock = RLock()
        self.parallelism_analyzer = parallelism_analyzer or ParallelismAnalyzer()

    def autoscale_workers(
        self,
        telemetry: Dict[str, Any],
        current_workers: int = 4,
        max_worker_cap: int = 32,
    ) -> ParallelismAutoscaleDecision:
        """
        Evaluates shared runtime telemetry to compute optimal worker count.
        """
        with self._lock:
            cpu = telemetry.get("cpu_percent", 50.0)
            mem = telemetry.get("memory_utilization_pct", 50.0)
            conn_pool_util = telemetry.get("connection_pool_utilization_pct", 50.0)
            lock_wait_ms = telemetry.get("lock_wait_time_ms", 0.0)
            worker_util = telemetry.get("worker_utilization_pct", 70.0)
            queue_depth = telemetry.get("queue_depth", 0)

            new_workers = current_workers
            direction = "NONE"
            reasons = []

            # Hard scaling constraints check (downscale conditions)
            if cpu > 88.0 or mem > 88.0 or conn_pool_util > 92.0 or lock_wait_ms > 150.0:
                new_workers = max(1, current_workers - 1)
                direction = "DOWN"
                if cpu > 88.0:
                    reasons.append(f"CPU pressure elevated ({cpu:.1f}%)")
                if mem > 88.0:
                    reasons.append(f"RAM memory pressure elevated ({mem:.1f}%)")
                if conn_pool_util > 92.0:
                    reasons.append(f"Connection pool saturated ({conn_pool_util:.1f}%)")
                if lock_wait_ms > 150.0:
                    reasons.append(f"Database lock wait time high ({lock_wait_ms:.1f} ms)")

            # Upscale conditions (headroom available & queue backlog)
            elif cpu < 65.0 and mem < 75.0 and conn_pool_util < 75.0 and lock_wait_ms < 20.0:
                if queue_depth > 50 or worker_util > 80.0:
                    new_workers = min(max_worker_cap, current_workers + 1)
                    direction = "UP"
                    reasons.append(f"Capacity available (CPU {cpu:.1f}%, RAM {mem:.1f}%) with queue depth ({queue_depth})")

            if not reasons:
                reasons.append("Worker pool concurrency in optimal steady state.")

            is_event = new_workers != current_workers

            return ParallelismAutoscaleDecision(
                current_workers=current_workers,
                recommended_workers=new_workers,
                parallel_chunks=new_workers * 2,
                is_scaling_event=is_event,
                scaling_direction=direction,
                reason="; ".join(reasons),
            )

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        c_workers = current_config.get("worker_count", 4)
        decision = self.autoscale_workers(metrics, current_workers=c_workers)
        if decision.is_scaling_event:
            return {
                "worker_count": decision.recommended_workers,
                "parallel_chunks": decision.parallel_chunks,
            }
        return None
