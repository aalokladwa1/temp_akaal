"""
gRPC Servicer Implementation for akaal.v1.
"""

from typing import AsyncGenerator
import json
from akaal.api.contracts.dto import JobRequestDTO, WorkflowSubmitDTO
from akaal.api.facades.platform1 import Platform1Facade
from akaal.api.facades.platform2 import Platform2Facade


class AkaalV1Servicer:
    """Async gRPC Servicer handling akaal.v1 RPC calls."""

    def __init__(
        self,
        platform1_facade: Platform1Facade = None,
        platform2_facade: Platform2Facade = None,
    ) -> None:
        self.p1_facade = platform1_facade or Platform1Facade()
        self.p2_facade = platform2_facade or Platform2Facade()

    async def SubmitJob(self, request_data: dict) -> dict:
        """Unary RPC: Submit Job."""
        payload = json.loads(request_data.get("payload_json", "{}"))
        dto = JobRequestDTO(
            job_type=request_data.get("job_type", "default"),
            payload=payload,
            priority=request_data.get("priority", 5),
            tenant_id=request_data.get("tenant_id"),
        )
        res = await self.p1_facade.submit_job(dto)
        return {
            "job_id": res.job_id,
            "status": res.status,
            "created_at": res.created_at,
            "message": res.message,
        }

    async def GetJobStatus(self, request_data: dict) -> dict:
        """Unary RPC: Query Job Status."""
        res = await self.p1_facade.get_job_status(request_data["job_id"])
        return {
            "job_id": res.job_id,
            "status": res.status,
            "progress_percentage": res.progress_percentage,
            "created_at": res.created_at,
            "updated_at": res.updated_at,
            "error_message": res.error_message or "",
        }

    async def StreamJobLogs(self, request_data: dict) -> AsyncGenerator[dict, None]:
        """Server Streaming RPC: Stream Job Logs."""
        job_id = request_data["job_id"]
        async for line in self.p1_facade.stream_job_logs(job_id):
            yield {"timestamp": "2026-07-22T12:00:00Z", "log_line": line}

    async def ExecuteWorkflow(self, request_data: dict) -> dict:
        """Unary RPC: Execute Workflow."""
        dto = WorkflowSubmitDTO(
            workflow_id=request_data["workflow_id"],
            name=request_data.get("name", "workflow"),
            description=request_data.get("description", ""),
            steps=json.loads(request_data.get("manifest_json", "[]")),
            tenant_id=request_data.get("tenant_id"),
        )
        res = await self.p1_facade.execute_workflow(dto)
        return {
            "workflow_id": res.workflow_id,
            "status": res.status,
            "total_steps": res.total_steps,
            "duration_ms": res.duration_ms,
        }

    async def GetClusterStatus(self, request_data: dict) -> dict:
        """Unary RPC: Get Worker Cluster Status."""
        res = await self.p2_facade.get_worker_cluster_status()
        return {
            "cluster_id": res.cluster_id,
            "active_workers": res.active_workers,
            "idle_workers": res.idle_workers,
            "cluster_health": res.cluster_health,
        }
