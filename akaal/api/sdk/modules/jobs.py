"""
SDK JobApi Module.
"""

from akaal.api.contracts.dto import JobRequestDTO, JobResponseDTO, JobStatusDTO
from akaal.api.facades.platform1 import Platform1Facade
from akaal.api.resilience.retry import RetryPolicy


class JobApi:
    """Async Job Client for SDK."""

    def __init__(self, facade: Platform1Facade = None) -> None:
        self.facade = facade or Platform1Facade()
        self.retry_policy = RetryPolicy(max_retries=3)

    async def submit(self, job_type: str, payload: dict, priority: int = 5) -> JobResponseDTO:
        dto = JobRequestDTO(job_type=job_type, payload=payload, priority=priority)
        return await self.retry_policy.execute(self.facade.submit_job, dto)

    async def get_status(self, job_id: str) -> JobStatusDTO:
        return await self.retry_policy.execute(self.facade.get_job_status, job_id)

    async def cancel(self, job_id: str, reason: str = "SDK user cancelled") -> bool:
        return await self.retry_policy.execute(self.facade.cancel_job, job_id, reason=reason)
