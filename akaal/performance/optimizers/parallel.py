"""
Intelligent Parallel Execution Manager.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class ParallelExecutionManager(PluginOptimizer):
    """Allocates worker threads and splits tables/partitions into dynamic parallel chunks."""

    def __init__(self) -> None:
        super().__init__("parallel")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_workers = current_config.get("worker_count", 4)
        cpu = metrics.get("cpu_percent", 50.0)
        queue_depth = metrics.get("queue_depth", 0)

        new_workers = current_workers
        if cpu > 90.0:
            # Scale down concurrency to resolve thread contention & context switching
            new_workers = max(current_workers - 1, 1)
        elif cpu < 60.0 and queue_depth > 50:
            # Add workers to clear backlog
            new_workers = min(current_workers + 1, 16)

        if new_workers != current_workers:
            return {"worker_count": new_workers, "parallel_chunks": new_workers * 2}
        return None
