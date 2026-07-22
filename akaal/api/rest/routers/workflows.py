"""
Workflow REST API Router (/api/v1/workflows).
"""

from fastapi import APIRouter, HTTPException
from akaal.api.contracts.dto import WorkflowSubmitDTO, WorkflowTraceDTO
from akaal.api.facades.platform1 import Platform1Facade

router = APIRouter(prefix="/workflows", tags=["Workflows"])
platform1_facade = Platform1Facade()


@router.post("/execute", response_model=WorkflowTraceDTO)
async def execute_workflow(request: WorkflowSubmitDTO):
    """Submit and execute a workflow manifest."""
    try:
        return await platform1_facade.execute_workflow(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
