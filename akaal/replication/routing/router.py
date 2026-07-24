"""IntelligentReplicationRouter & AdaptiveStrategySwitcher."""

from typing import List, Dict, Any
from akaal.replication.core.models import ReplicationMode


class IntelligentReplicationRouter:
    """Selects optimal network and replication path for target nodes."""

    def select_route(self, source_node: str, target_node: str) -> List[str]:
        return [source_node, f"bridge_{source_node}_{target_node}", target_node]


class AdaptiveStrategySwitcher:
    """Dynamically switches replication modes based on lag and network health."""

    def determine_optimal_mode(self, current_lag_ms: float, error_rate: float) -> ReplicationMode:
        if current_lag_ms > 10000.0 or error_rate > 0.05:
            return ReplicationMode.ACTIVE_PASSIVE
        return ReplicationMode.ACTIVE_ACTIVE
