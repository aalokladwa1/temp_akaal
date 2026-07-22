"""
SDK MonitoringApi Module.
"""

from akaal.api.contracts.dto import ClusterStatusDTO
from akaal.api.facades.platform2 import Platform2Facade
from akaal.api.resilience.retry import RetryPolicy


class MonitoringApi:
    """Async Monitoring Client for SDK."""

    def __init__(self, facade: Platform2Facade = None) -> None:
        self.facade = facade or Platform2Facade()
        self.retry_policy = RetryPolicy(max_retries=3)

    async def get_cluster_status(self) -> ClusterStatusDTO:
        return await self.retry_policy.execute(self.facade.get_worker_cluster_status)
