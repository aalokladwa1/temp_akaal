"""
Adaptive Connection Pool Optimizer.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class ConnectionPoolOptimizer(PluginOptimizer):
    """Self-tunes active database connection pool ranges to limit connection latency spikes."""

    def __init__(self) -> None:
        super().__init__("connection_pool")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_size = current_config.get("pool_max_connections", 10)
        db_response_time = metrics.get("db_response_time_ms", 5.0)
        active_transactions = metrics.get("active_transactions", 0)

        new_size = current_size
        if db_response_time > 100.0:
            # High DB response time => reduce pool size to allow database to clear queries
            new_size = max(current_size - 2, 5)
        elif active_transactions > current_size * 0.8 and db_response_time < 20.0:
            # Lots of free connections needed with quick response time => grow pool
            new_size = min(current_size + 2, 50)

        if new_size != current_size:
            return {"pool_max_connections": new_size}
        return None
