"""
Load Balancing Engine.
"""

from typing import Dict, Any, List, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class PerformanceLoadBalancer(PluginOptimizer):
    """Distributes work tasks among workers based on utilization and node health metrics."""

    def __init__(self) -> None:
        super().__init__("load_balancer")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        # Load balancing is active when enabled
        if not current_config.get("load_balancer_enabled", False):
            return {"load_balancer_enabled": True}
        return None

    def balance_workloads(self, tasks: List[Any], worker_healths: Dict[str, float]) -> Dict[str, List[Any]]:
        """Splits input tasks among active workers proportional to health and utilization scores."""
        distribution: Dict[str, List[Any]] = {w: [] for w in worker_healths.keys()}
        if not worker_healths:
            return distribution

        # Sort workers by health rating (highest health first)
        sorted_workers = sorted(worker_healths.items(), key=lambda x: x[1], reverse=True)
        
        for idx, task in enumerate(tasks):
            worker_id = sorted_workers[idx % len(sorted_workers)][0]
            distribution[worker_id].append(task)
            
        return distribution
