"""
SDK ReportingApi Module.
"""

from akaal.api.contracts.dto import ReportDTO
from akaal.api.facades.platform8 import Platform8Facade
from akaal.api.resilience.retry import RetryPolicy


class ReportingApi:
    """Async Reporting Client for SDK."""

    def __init__(self, facade: Platform8Facade = None) -> None:
        self.facade = facade or Platform8Facade()
        self.retry_policy = RetryPolicy(max_retries=3)

    async def get_report(self, report_id: str) -> ReportDTO:
        return await self.retry_policy.execute(self.facade.get_report, report_id)
