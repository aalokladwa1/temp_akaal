"""Hierarchical Enterprise Retry System."""

from typing import Dict, Optional
from akaal.workflow.execution.policies import ExponentialRetryPolicy, IRetryPolicy


class RetryPolicyHierarchy:
    """Manages 8-tier hierarchy of retry policies for granular failure recovery."""

    def __init__(self) -> None:
        self.workflow_retry = ExponentialRetryPolicy(max_retries=3)
        self.step_retry = ExponentialRetryPolicy(max_retries=3)
        self.activity_retry = ExponentialRetryPolicy(max_retries=5)
        self.worker_retry = ExponentialRetryPolicy(max_retries=2)
        self.lease_retry = ExponentialRetryPolicy(max_retries=5)
        self.queue_retry = ExponentialRetryPolicy(max_retries=5)
        self.network_retry = ExponentialRetryPolicy(max_retries=3)
        self.database_retry = ExponentialRetryPolicy(max_retries=3)

    def get_policy_for_tier(self, tier: str) -> IRetryPolicy:
        tier_lower = tier.lower()
        if "workflow" in tier_lower:
            return self.workflow_retry
        if "step" in tier_lower:
            return self.step_retry
        if "activity" in tier_lower:
            return self.activity_retry
        if "worker" in tier_lower:
            return self.worker_retry
        if "lease" in tier_lower:
            return self.lease_retry
        if "queue" in tier_lower:
            return self.queue_retry
        if "network" in tier_lower:
            return self.network_retry
        if "database" in tier_lower or "db" in tier_lower:
            return self.database_retry
        return self.step_retry
