"""Decision Context and Risk Evaluator for Replication Decision Engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DecisionContext:
    """Contextual metrics evaluated before executing a replication action."""

    replica_health_score: float = 100.0
    replication_lag_ms: float = 10.0
    sla_max_lag_ms: float = 5000.0
    network_status: str = "HEALTHY"
    business_criticality: str = "MEDIUM"
    policy_profile: str = "AUTOMATIC"
    cluster_health: str = "HEALTHY"
    has_active_lock: bool = False
    error_count: int = 0


class ReplicationRiskEvaluator:
    """Computes risk score (0.0 to 100.0) for replication operations."""

    def evaluate_risk(self, ctx: DecisionContext) -> float:
        risk = 5.0
        if ctx.replica_health_score < 80.0:
            risk += 30.0
        if ctx.replication_lag_ms > ctx.sla_max_lag_ms:
            risk += 35.0
        if ctx.network_status != "HEALTHY":
            risk += 25.0
        if ctx.business_criticality == "CRITICAL":
            risk += 15.0
        if ctx.error_count > 3:
            risk += 20.0
        return min(risk, 100.0)
