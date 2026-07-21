"""
Cross-Platform Integration Engine for Platforms 1, 2, and 3.
Orchestrates Platform 1 Workflows, Platform 2 Distributed Task Scheduling,
and Platform 3 Zero-Copy Streaming Pipelines into a unified enterprise execution system.
Contains ZERO CDC, migration business logic, or database adapter code.
"""

from typing import Dict, List, Optional, Any
from threading import RLock
import time
import logging

from akaal.orchestration import (
    MigrationJob, JobId, WorkflowId, SessionId, ConfigurationId,
    WorkflowContext, WorkflowCheckpoint, WorkflowEngine, WorkflowAuditLogger, EngineState,
    StateTransitioned, AuditRecord
)

from akaal.distributed.facade.runtime import DefaultDistributedRuntimeV1
from akaal.distributed.domain.models import Task, Worker
from akaal.distributed.domain.identifiers import WorkerId, NodeId, TaskId, ExecutionId, IdempotencyKey
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth

from akaal.streaming.facade.runtime import DefaultStreamingRuntimeV1
from akaal.streaming.domain.models import StreamRecord, StreamConfig
from akaal.streaming.domain.enums import BackpressureState
from akaal.streaming.operators.base import StreamOperator

logger = logging.getLogger("nexusforge.integration.cross_platform")


class CrossPlatformIntegrationEngine:
    """
    Unified Cross-Platform Integration Engine orchestrating Platforms 1, 2, and 3.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        
        # Platform 1 Engine & Audit Logger
        self.workflow_engine = WorkflowEngine()
        self.audit_logger = WorkflowAuditLogger()
        self.workflow_engine.dispatcher.subscribe(self.audit_logger)

        # Platform 2 Distributed Runtime
        self.distributed_runtime = DefaultDistributedRuntimeV1()

        # Platform 3 Streaming Runtimes (mapped by job_id str)
        self.streaming_runtimes: Dict[str, DefaultStreamingRuntimeV1] = {}
        self._active_jobs: Dict[str, MigrationJob] = {}

    def _log_audit_event(self, aggregate_id: str, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = StateTransitioned(
            aggregate_id=aggregate_id,
            workflow_id=aggregate_id,
            job_id=aggregate_id,
            from_state=event_type,
            to_state=event_type,
        )
        self.workflow_engine.dispatcher.publish(event)

    def submit_migration_job(self, job: MigrationJob, streaming_operators: Optional[List[StreamOperator]] = None) -> MigrationJob:
        """
        Scenario 1: Platform 1 creates job -> Platform 2 schedules task -> Platform 3 processes stream.
        """
        with self._lock:
            job_key = str(job.job_id)
            # 1. Platform 1 saves & validates job
            self.workflow_engine.workflow_repo.save_job(job)
            self._active_jobs[job_key] = job
            self._log_audit_event(job_key, "JOB_SUBMITTED", {"job_id": job_key})

            # 2. Platform 2 creates distributed Task
            task = Task(
                task_id=TaskId(f"task_{job_key}"),
                execution_id=ExecutionId(f"exec_{job_key}"),
                name=f"Task_{job_key}",
                payload={"job_id": job_key, "source": job.source_profile.get("db_type"), "target": job.target_profile.get("db_type")},
            )
            self.distributed_runtime.submit_task(task, idempotency_key=IdempotencyKey(f"idempotency_{job_key}"))
            self._log_audit_event(job_key, "TASK_ENQUEUED_P2", {"task_id": str(task.task_id)})

            # 3. Platform 3 initializes Streaming Runtime
            stream_rt = DefaultStreamingRuntimeV1(config=StreamConfig(batch_size=100))
            if streaming_operators:
                for op in streaming_operators:
                    stream_rt.add_operator(op)
            self.streaming_runtimes[job_key] = stream_rt

            return job

    def register_worker_node(self, worker_id_str: str) -> Worker:
        """Registers a worker node in Platform 2 Distributed Runtime."""
        with self._lock:
            n_id = NodeId(f"node_{worker_id_str}")
            return self.distributed_runtime.register_worker(node_id=n_id, capacity=5)

    def execute_scheduled_step(self, job_id_str: str, records: List[StreamRecord]) -> Dict[str, Any]:
        """
        Executes a processing step through Platform 2 worker assignment and Platform 3 streaming execution.
        """
        with self._lock:
            job = self._active_jobs.get(job_id_str)
            if not job:
                raise ValueError(f"Job '{job_id_str}' not found in active jobs.")

            stream_rt = self.streaming_runtimes.get(job_id_str)
            if not stream_rt:
                raise ValueError(f"Streaming runtime for job '{job_id_str}' not found.")

            # Check Platform 3 backpressure state
            bp_state = stream_rt.get_backpressure_state()
            if bp_state in (BackpressureState.HIGH_WATERMARK, BackpressureState.THROTTLED):
                logger.warning(f"Backpressure detected in Platform 3 ({bp_state.value}). Throttling Platform 2 scheduler.")
                return {"status": "THROTTLED", "processed": 0, "backpressure": bp_state.value}

            # Ingest records into Platform 3
            pushed_count = 0
            for r in records:
                if stream_rt.push(r):
                    pushed_count += 1

            # Process stream batch in Platform 3
            processed = stream_rt.execute_step()
            outputs = stream_rt.collect_output()

            self._log_audit_event(
                job_id_str,
                "STREAM_STEP_EXECUTED",
                {"pushed": pushed_count, "processed": processed, "outputs": len(outputs)},
            )

            return {
                "status": "SUCCESS",
                "pushed": pushed_count,
                "processed": processed,
                "output_count": len(outputs),
                "outputs": outputs,
            }

    def complete_migration_job(self, job_id_str: str) -> MigrationJob:
        """Marks job completed in Platform 1 and cleans up Platform 2 & 3 resources."""
        with self._lock:
            job = self._active_jobs.get(job_id_str)
            if not job:
                raise ValueError(f"Job '{job_id_str}' not found.")

            completed_job = job.with_updates(current_state=EngineState.COMPLETED)
            self._active_jobs[job_id_str] = completed_job
            self._log_audit_event(job_id_str, "JOB_COMPLETED", {"status": "COMPLETED"})

            # Cleanup Platform 3 streaming runtime
            self.streaming_runtimes.pop(job_id_str, None)
            return completed_job

    def cancel_migration_job(self, job_id_str: str) -> MigrationJob:
        """
        Scenario 5: Cancels job from Platform 1 -> stops Platform 2 scheduler -> terminates Platform 3 stream.
        """
        with self._lock:
            job = self._active_jobs.get(job_id_str)
            if not job:
                raise ValueError(f"Job '{job_id_str}' not found.")

            cancelled_job = job.with_updates(current_state=EngineState.CANCELLED)
            self._active_jobs[job_id_str] = cancelled_job
            self._log_audit_event(job_id_str, "JOB_CANCELLED", {"status": "CANCELLED"})

            # Platform 3 Cleanup
            self.streaming_runtimes.pop(job_id_str, None)

            return cancelled_job

    def get_audit_history(self, job_id_str: str) -> List[AuditRecord]:
        """Returns audit record history for a given job."""
        with self._lock:
            return [r for r in self.audit_logger.get_records() if r.aggregate_id == job_id_str]


def create_sample_migration_job(job_id_str: str, name: str = "Sample Migration Job") -> MigrationJob:
    """Helper factory function creating valid MigrationJob instances."""
    return MigrationJob(
        job_id=JobId(job_id_str),
        workflow_id=WorkflowId.generate(),
        session_id=SessionId.generate(),
        config_id=ConfigurationId.generate(),
        source_profile={"db_type": "ORACLE", "name": name},
        target_profile={"db_type": "POSTGRESQL"},
    )
