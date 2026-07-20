"""Checkpoint Storage Contracts and Adapters (Memory and File)."""

import json
from pathlib import Path
from typing import Protocol, Tuple
from akaal.workflow.exceptions import CheckpointCorruptException, CheckpointNotFoundException
from akaal.workflow.models.checkpoint import WorkflowCheckpoint
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.sub_contexts import ExecutionContext, RuntimeContext, UserContext
from akaal.workflow.security.security_context import SecurityContext
from akaal.workflow.utils.serialization import compute_sha256, verify_sha256


class ICheckpointStorage(Protocol):
    """Abstract repository contract for persisting and loading checkpoints."""

    def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Persist a workflow checkpoint snapshot."""
        ...

    def load_latest_checkpoint(self, workflow_id: str, run_id: str) -> WorkflowCheckpoint | None:
        """Load the most recent checkpoint for a workflow run."""
        ...

    def load_checkpoint_by_id(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        """Load a specific checkpoint by its unique ID."""
        ...

    def list_checkpoints(self, workflow_id: str) -> Tuple[WorkflowCheckpoint, ...]:
        """List all checkpoints stored for a workflow ID."""
        ...


class InMemoryCheckpointStorage:
    """In-memory checkpoint repository for testing and single-node runs."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, WorkflowCheckpoint] = {}  # checkpoint_id -> checkpoint

    def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        # Validate integrity before saving
        if not verify_sha256(checkpoint.to_dict(), checkpoint.checksum):
            raise CheckpointCorruptException(checkpoint.checkpoint_id, "Checksum verification failed")
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    def load_latest_checkpoint(self, workflow_id: str, run_id: str) -> WorkflowCheckpoint | None:
        matches = [
            cp for cp in self._checkpoints.values()
            if cp.workflow_id == workflow_id and cp.run_id == run_id
        ]
        if not matches:
            return None
        # Sort by creation time / version
        matches.sort(key=lambda cp: cp.created_at, reverse=True)
        latest = matches[0]
        if not verify_sha256(latest.to_dict(), latest.checksum):
            raise CheckpointCorruptException(latest.checkpoint_id, "Checksum verification failed on load")
        return latest

    def load_checkpoint_by_id(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        cp = self._checkpoints.get(checkpoint_id)
        if cp and not verify_sha256(cp.to_dict(), cp.checksum):
            raise CheckpointCorruptException(checkpoint_id, "Checksum verification failed on load")
        return cp

    def list_checkpoints(self, workflow_id: str) -> Tuple[WorkflowCheckpoint, ...]:
        matches = [cp for cp in self._checkpoints.values() if cp.workflow_id == workflow_id]
        matches.sort(key=lambda cp: cp.created_at)
        return tuple(matches)


class FileBasedCheckpointStorage:
    """File-system checkpoint storage using JSON files."""

    def __init__(self, storage_dir: str | Path) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        file_path = self._storage_dir / f"{checkpoint.checkpoint_id}.json"
        data = checkpoint.to_dict()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_latest_checkpoint(self, workflow_id: str, run_id: str) -> WorkflowCheckpoint | None:
        all_cps = self.list_checkpoints(workflow_id)
        matches = [cp for cp in all_cps if cp.run_id == run_id]
        if not matches:
            return None
        matches.sort(key=lambda cp: cp.created_at, reverse=True)
        return matches[0]

    def load_checkpoint_by_id(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        file_path = self._storage_dir / f"{checkpoint_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._deserialize_checkpoint(data)

    def list_checkpoints(self, workflow_id: str) -> Tuple[WorkflowCheckpoint, ...]:
        cps: list[WorkflowCheckpoint] = []
        for file_path in self._storage_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("workflow_id") == workflow_id:
                cps.append(self._deserialize_checkpoint(data))
        cps.sort(key=lambda cp: cp.created_at)
        return tuple(cps)

    def _deserialize_checkpoint(self, data: dict) -> WorkflowCheckpoint:
        chk_checksum = data.get("checksum", "")
        # Reconstruct WorkflowContext
        ctx_data = data["context"]
        exec_data = ctx_data["execution_context"]
        rt_data = ctx_data["runtime_context"]
        user_data = ctx_data["user_context"]
        sec_data = user_data["security_context"]

        sec_context = SecurityContext(
            user_id=sec_data["user_id"],
            tenant_id=sec_data["tenant_id"],
            roles=tuple(sec_data.get("roles", ())),
            permissions=tuple(sec_data.get("permissions", ())),
            token_id=sec_data.get("token_id"),
        )
        user_context = UserContext(
            user_id=user_data["user_id"],
            tenant_id=user_data["tenant_id"],
            security_context=sec_context,
            granted_permissions=tuple(user_data.get("granted_permissions", ())),
            correlation_id=user_data.get("correlation_id", "corr-default"),
            trace_parent=user_data.get("trace_parent"),
        )
        runtime_context = RuntimeContext(
            environment_variables=dict(rt_data.get("environment_variables", {})),
            transient_parameters=dict(rt_data.get("transient_parameters", {})),
            runtime_flags=dict(rt_data.get("runtime_flags", {})),
            temporary_state=dict(rt_data.get("temporary_state", {})),
        )
        execution_context = ExecutionContext(
            workflow_id=exec_data["workflow_id"],
            run_id=exec_data["run_id"],
            completed_steps=tuple(exec_data.get("completed_steps", ())),
            pending_steps=tuple(exec_data.get("pending_steps", ())),
            retry_counts=dict(exec_data.get("retry_counts", {})),
            checkpoint_reference=exec_data.get("checkpoint_reference"),
            step_metrics=dict(exec_data.get("step_metrics", {})),
        )
        context = WorkflowContext(
            execution_context=execution_context,
            runtime_context=runtime_context,
            user_context=user_context,
            version=ctx_data.get("version", 1),
        )
        cp = WorkflowCheckpoint(
            checkpoint_id=data["checkpoint_id"],
            workflow_id=data["workflow_id"],
            run_id=data["run_id"],
            step_id=data["step_id"],
            state=data["state"],
            context=context,
            completed_steps=tuple(data.get("completed_steps", ())),
            pending_steps=tuple(data.get("pending_steps", ())),
            created_at=data.get("created_at", "2026-01-01T00:00:00+00:00"),
        )
        if chk_checksum and cp.checksum != chk_checksum:
            raise CheckpointCorruptException(data["checkpoint_id"], "Checksum mismatch on load")
        return cp
