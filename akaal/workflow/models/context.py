"""Composition Root Model for WorkflowContext."""

from dataclasses import dataclass, field, replace
from typing import Any
from akaal.workflow.models.sub_contexts import ExecutionContext, RuntimeContext, UserContext
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """Immutable composition root aggregating ExecutionContext, RuntimeContext, and UserContext."""

    execution_context: ExecutionContext
    runtime_context: RuntimeContext = field(default_factory=RuntimeContext)
    user_context: UserContext = field(default_factory=UserContext)
    version: int = 1
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "execution_context": self.execution_context.to_dict(),
            "runtime_context": self.runtime_context.to_dict(),
            "user_context": self.user_context.to_dict(),
            "version": self.version,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    @property
    def workflow_id(self) -> str:
        return self.execution_context.workflow_id

    @property
    def run_id(self) -> str:
        return self.execution_context.run_id

    def with_updates(
        self,
        execution_updates: dict[str, Any] | None = None,
        runtime_updates: dict[str, Any] | None = None,
        user_updates: dict[str, Any] | None = None,
    ) -> "WorkflowContext":
        """Pure functional update returning a new WorkflowContext with incremented version."""
        new_exec = self.execution_context
        if execution_updates:
            exec_dict = self.execution_context.to_dict()
            exec_dict.pop("checksum", None)
            exec_dict.update(execution_updates)
            new_exec = ExecutionContext(
                workflow_id=exec_dict["workflow_id"],
                run_id=exec_dict["run_id"],
                completed_steps=tuple(exec_dict.get("completed_steps", ())),
                pending_steps=tuple(exec_dict.get("pending_steps", ())),
                retry_counts=dict(exec_dict.get("retry_counts", {})),
                checkpoint_reference=exec_dict.get("checkpoint_reference"),
                step_metrics=dict(exec_dict.get("step_metrics", {})),
            )

        new_rt = self.runtime_context
        if runtime_updates:
            rt_dict = self.runtime_context.to_dict()
            rt_dict.pop("checksum", None)
            # Update nested temporary_state or root keys
            if "temporary_state" in runtime_updates and isinstance(runtime_updates["temporary_state"], dict):
                temp = dict(rt_dict.get("temporary_state", {}))
                temp.update(runtime_updates["temporary_state"])
                rt_dict["temporary_state"] = temp
            for k, v in runtime_updates.items():
                if k != "temporary_state":
                    rt_dict[k] = v
            new_rt = RuntimeContext(
                environment_variables=dict(rt_dict.get("environment_variables", {})),
                transient_parameters=dict(rt_dict.get("transient_parameters", {})),
                runtime_flags=dict(rt_dict.get("runtime_flags", {})),
                temporary_state=dict(rt_dict.get("temporary_state", {})),
            )

        new_user = self.user_context
        if user_updates:
            user_dict = self.user_context.to_dict()
            user_dict.pop("checksum", None)
            user_dict.update(user_updates)
            sec = user_dict.get("security_context")
            if isinstance(sec, dict):
                sec = self.user_context.security_context
            new_user = UserContext(
                user_id=user_dict["user_id"],
                tenant_id=user_dict["tenant_id"],
                security_context=sec,
                granted_permissions=tuple(user_dict.get("granted_permissions", ())),
                correlation_id=user_dict.get("correlation_id", "correlation-default"),
                trace_parent=user_dict.get("trace_parent"),
            )

        return replace(
            self,
            execution_context=new_exec,
            runtime_context=new_rt,
            user_context=new_user,
            version=self.version + 1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_context": self.execution_context.to_dict(),
            "runtime_context": self.runtime_context.to_dict(),
            "user_context": self.user_context.to_dict(),
            "version": self.version,
            "checksum": self.checksum,
        }
