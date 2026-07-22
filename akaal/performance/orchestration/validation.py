"""
Post-Optimization Metrics Validation.
"""

from typing import Dict, Any


class PostOptimizationValidator:
    """Compares baseline metrics against post-optimization metrics to verify improvement."""

    @staticmethod
    def validate(baseline: Dict[str, Any], post: Dict[str, Any], allowed_degradation: float = 0.05) -> bool:
        """
        Returns True if metrics show improvement or stay within allowed_degradation bounds.
        Returns False if post-optimization is significantly slower or more resource intensive.
        """
        base_latency = baseline.get("latency_ms", 0.0)
        post_latency = post.get("latency_ms", 0.0)

        # 1. Latency comparison (lower latency is better)
        if base_latency > 0.0 and post_latency > 0.0:
            latency_increase = (post_latency - base_latency) / base_latency
            if latency_increase > allowed_degradation:
                # Performance degraded beyond bounds
                return False

        # 2. Throughput comparison (higher throughput is better)
        base_tp = baseline.get("throughput_records_sec", 0.0)
        post_tp = post.get("throughput_records_sec", 0.0)
        if base_tp > 0.0 and post_tp > 0.0:
            tp_decrease = (base_tp - post_tp) / base_tp
            if tp_decrease > allowed_degradation:
                # Throughput dropped significantly
                return False

        return True
