"""Priority Aging Algorithm for Task Starvation Prevention."""

from akaal.workflow.queues.interfaces import StepExecutionTask


class PriorityAgingAlgorithm:
    """Calculates dynamic task priority using aging formula to prevent starvation."""

    def __init__(self, alpha: float = 1.0, beta: float = 0.5) -> None:
        self.alpha = alpha
        self.beta = beta

    def calculate_effective_priority(
        self,
        task: StepExecutionTask,
        wait_time_seconds: float,
        tenant_usage_ratio: float = 0.0,
    ) -> int:
        """EffectivePriority = BasePriority + alpha * WaitTime - beta * TenantUsageRatio."""
        aging_boost = self.alpha * (wait_time_seconds / 60.0)
        quota_penalty = self.beta * tenant_usage_ratio * 10.0
        effective = int(task.priority + aging_boost - quota_penalty)
        return max(0, min(100, effective))
