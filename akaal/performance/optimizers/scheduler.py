"""
Adaptive Resource Scheduler.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class ResourceSchedulerOptimizer(PluginOptimizer):
    """Adjusts task prioritize levels and concurrency pacing based on CPU/RAM/Disk IO stress."""

    def __init__(self) -> None:
        super().__init__("scheduler")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_pacing_ms = current_config.get("scheduler_pacing_ms", 0)
        cpu = metrics.get("cpu_percent", 50.0)
        io_wait = metrics.get("disk_io_wait_percent", 10.0)

        new_pacing = current_pacing_ms
        if cpu > 85.0 or io_wait > 30.0:
            # Introduce pacing delays to throttle CPU/Disk IO load
            new_pacing = max(current_pacing_ms + 10, 50)
        elif cpu < 50.0 and io_wait < 10.0:
            # Decrease delay for high speed throughput
            new_pacing = max(current_pacing_ms - 10, 0)

        if new_pacing != current_pacing_ms:
            return {"scheduler_pacing_ms": new_pacing}
        return None
