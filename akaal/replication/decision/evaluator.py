"""DecisionEvaluator for evaluating replication choices."""

from enum import Enum
from akaal.replication.decision.context import DecisionContext, ReplicationRiskEvaluator


class ReplicationDecisionChoice(str, Enum):
    REPLICATE = "REPLICATE"
    RETRY = "RETRY"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    REROUTE = "REROUTE"
    FAILOVER = "FAILOVER"
    ROLLBACK = "ROLLBACK"
    IGNORE = "IGNORE"


class DecisionEvaluator:
    """Evaluates whether to REPLICATE, RETRY, PAUSE, RESUME, REROUTE, FAILOVER, ROLLBACK, or IGNORE."""

    def __init__(self):
        self.risk_evaluator = ReplicationRiskEvaluator()

    def evaluate(self, ctx: DecisionContext) -> ReplicationDecisionChoice:
        risk = self.risk_evaluator.evaluate_risk(ctx)

        if ctx.cluster_health == "UNHEALTHY" or ctx.replica_health_score < 40.0:
            return ReplicationDecisionChoice.FAILOVER
        elif risk > 85.0 and ctx.policy_profile == "STRICT_FINANCE":
            return ReplicationDecisionChoice.PAUSE
        elif risk > 90.0:
            return ReplicationDecisionChoice.ROLLBACK
        elif ctx.network_status == "DEGRADED":
            return ReplicationDecisionChoice.REROUTE
        elif ctx.replication_lag_ms > ctx.sla_max_lag_ms:
            return ReplicationDecisionChoice.RETRY
        else:
            return ReplicationDecisionChoice.REPLICATE
