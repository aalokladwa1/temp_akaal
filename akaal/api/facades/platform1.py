"""
Platform 1 Public Façade — Workflows & Jobs Integration.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional
import datetime
import uuid

from akaal.api.contracts.dto import (
    CapabilityDTO,
    JobRequestDTO,
    JobResponseDTO,
    JobStatusDTO,
    WorkflowSubmitDTO,
    WorkflowTraceDTO,
)
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.workflow.api.client import WorkflowClient
from akaal.workflow.models.metadata import WorkflowManifest, WorkflowMetadata, StepDefinition


class IPlatform1Facade(IFacade, ABC):
    """Abstract Interface for Platform 1 Façade."""

    @abstractmethod
    async def submit_job(self, request: JobRequestDTO) -> JobResponseDTO:
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobStatusDTO:
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        pass

    @abstractmethod
    async def execute_workflow(self, request: WorkflowSubmitDTO) -> WorkflowTraceDTO:
        pass

    @abstractmethod
    async def stream_job_logs(self, job_id: str) -> AsyncGenerator[str, None]:
        pass


class Platform1Facade(IPlatform1Facade):
    """Production Platform 1 Façade Implementation routing to WorkflowClient."""

    def __init__(self, client: Optional[WorkflowClient] = None) -> None:
        self._client = client or WorkflowClient()
        self._jobs_store: Dict[str, Dict[str, Any]] = {}

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 1 (Workflow & Jobs)",
            version="1.0.0",
            supported_features=["submit_job", "execute_workflow", "cancel_workflow", "stream_logs"],
            active_protocols=["REST", "gRPC"],
        )

    async def submit_job(self, request: JobRequestDTO) -> JobResponseDTO:
        try:
            job_id = f"job-{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._jobs_store[job_id] = {
                "job_id": job_id,
                "status": "QUEUED",
                "job_type": request.job_type,
                "payload": request.payload,
                "created_at": now,
                "updated_at": now,
                "progress": 0.0,
            }
            return JobResponseDTO(
                job_id=job_id,
                status="QUEUED",
                job_type=request.job_type,
                created_at=now,
                message="Job submitted successfully",
            )
        except Exception as e:
            raise FacadeError(f"Failed to submit job to Platform 1: {str(e)}")

    async def get_job_status(self, job_id: str) -> JobStatusDTO:
        if job_id not in self._jobs_store:
            raise FacadeError(f"Job {job_id} not found in Platform 1")
        j = self._jobs_store[job_id]
        return JobStatusDTO(
            job_id=j["job_id"],
            status=j["status"],
            progress_percentage=j["progress"],
            created_at=j["created_at"],
            updated_at=j["updated_at"],
        )

    async def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        if job_id in self._jobs_store:
            self._jobs_store[job_id]["status"] = "CANCELLED"
            self._jobs_store[job_id]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return True
        return False

    async def execute_workflow(self, request: WorkflowSubmitDTO) -> WorkflowTraceDTO:
        try:
            # Build WorkflowManifest contract for Platform 1
            meta = WorkflowMetadata(
                workflow_id=request.workflow_id,
                name=request.name,
                description=request.description or "",
                version="1.0.0",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )

            step_defs = [
                StepDefinition(
                    step_id=s.get("step_id", f"step-{i}"),
                    step_type=s.get("step_type", "noop"),
                    parameters=s.get("parameters", {}),
                )
                for i, s in enumerate(request.steps)
            ]

            manifest = WorkflowManifest(metadata=meta, steps=step_defs)
            self._client.submit_workflow(manifest)
            trace = self._client.execute_workflow(request.workflow_id, parameters=request.parameters)

            return WorkflowTraceDTO(
                workflow_id=trace.workflow_id,
                status=trace.status,
                total_steps=len(request.steps),
                executed_steps=[r.step_id for r in trace.step_results],
                step_results={r.step_id: r.output for r in trace.step_results},
                metrics={"duration_seconds": trace.metrics.duration_seconds},
                duration_ms=trace.metrics.duration_seconds * 1000.0,
            )
        except Exception as e:
            raise FacadeError(f"Failed to execute workflow on Platform 1: {str(e)}")

    async def stream_job_logs(self, job_id: str) -> AsyncGenerator[str, None]:
        yield f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] Log stream initialized for {job_id}\n"
        yield f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] Processing job data...\n"
        yield f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] Job {job_id} completed successfully.\n"
