"""
Operations REST API Router (/api/v1/ops).
"""

from fastapi import APIRouter
from akaal.api.contracts.dto import ClusterStatusDTO, WorkerScaleResultDTO
from akaal.api.facades.platform2 import Platform2Facade

router = APIRouter(prefix="/ops", tags=["Operations"])
platform2_facade = Platform2Facade()


@router.get("/cluster", response_model=ClusterStatusDTO)
async def get_cluster_status():
    """Get worker cluster status."""
    return await platform2_facade.get_worker_cluster_status()


@router.post("/workers/scale", response_model=WorkerScaleResultDTO)
async def scale_workers(target_count: int, pool_name: str = "default"):
    """Scale worker pool capacity."""
    return await platform2_facade.scale_workers(target_count, pool_name=pool_name)
