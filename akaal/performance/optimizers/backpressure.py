"""
Platform 3 Backpressure Optimizer.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class PerformanceBackpressureOptimizer(PluginOptimizer):
    """Adjusts backpressure thresholds and recovery delay timers dynamically."""

    def __init__(self) -> None:
        super().__init__("backpressure")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_high_watermark = current_config.get("bp_high_watermark", 1000)
        memory_usage = metrics.get("memory_utilization_percent", 50.0)

        new_high_watermark = current_high_watermark
        if memory_usage > 85.0:
            # Memory pressure is high => lower backpressure threshold to trigger early flow throttling
            new_high_watermark = max(int(current_high_watermark * 0.5), 100)
        elif memory_usage < 50.0:
            # Safe memory range => expand batch watermark queue limits
            new_high_watermark = min(int(current_high_watermark * 1.5), 5000)

        if new_high_watermark != current_high_watermark:
            return {"bp_high_watermark": new_high_watermark}
        return None
