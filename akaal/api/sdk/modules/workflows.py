"""
SDK WorkflowApi Module.
"""

from akaal.api.contracts.dto import WorkflowSubmitDTO, WorkflowTraceDTO
from akaal.api.facades.platform1 import Platform1Facade
from akaal.api.resilience.retry import RetryPolicy


class WorkflowApi:
    """Async Workflow Client for SDK."""

    def __init__(self, facade: Platform1Facade = None) -> None:
        self.facade = facade or Platform1Facade()
        self.retry_policy = RetryPolicy(max_retries=3)

    async def execute(self, workflow_id: str, steps: list, parameters: dict = None) -> WorkflowTraceDTO:
        dto = WorkflowSubmitDTO(
            workflow_id=workflow_id,
            name=f"Workflow {workflow_id}",
            steps=steps,
            parameters=parameters or {},
        )
        return await self.retry_policy.execute(self.facade.execute_workflow, dto)
