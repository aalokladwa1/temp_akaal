"""
Adaptive Batch Size Optimizer.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class AdaptiveBatchOptimizer(PluginOptimizer):
    """Dynamically self-adjusts batch size depending on load & transaction latency metrics."""

    def __init__(self) -> None:
        super().__init__("batch")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_batch = current_config.get("batch_size", 100)
        cpu = metrics.get("cpu_percent", 50.0)
        mem = metrics.get("memory_utilization_percent", 50.0)
        latency = metrics.get("latency_ms", 10.0)
        queue_depth = metrics.get("queue_depth", 0)

        # Self-adjustment math
        new_batch = current_batch
        if cpu > 85.0 or mem > 85.0 or latency > 80.0:
            # Scale down to ease memory pressure
            new_batch = max(int(current_batch * 0.7), 10)
        elif cpu < 40.0 and queue_depth > 100:
            # Scale up to leverage idle CPU
            new_batch = min(int(current_batch * 1.5), 1000)

        if new_batch != current_batch:
            return {"batch_size": new_batch}
        return None
