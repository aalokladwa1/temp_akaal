"""
Job REST API Router (/api/v1/jobs).
"""

from fastapi import APIRouter, HTTPException, Depends
from akaal.api.contracts.dto import JobRequestDTO, JobResponseDTO, JobStatusDTO
from akaal.api.facades.platform1 import Platform1Facade

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Dependency Singleton
platform1_facade = Platform1Facade()


@router.post("", response_model=JobResponseDTO)
async def submit_job(request: JobRequestDTO):
    """Submit a new job for execution."""
    return await platform1_facade.submit_job(request)


@router.get("/{job_id}", response_model=JobStatusDTO)
async def get_job_status(job_id: str):
    """Query job execution status."""
    try:
        return await platform1_facade.get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, reason: str = "User cancelled"):
    """Cancel a running or queued job."""
    success = await platform1_facade.cancel_job(job_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"status": "CANCELLED", "job_id": job_id, "reason": reason}
