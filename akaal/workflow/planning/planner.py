"""ExecutionPlanner converting Workflow Manifest DAGs into Executable Stages."""

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Tuple
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class ExecutionStage:
    """Stage grouping of steps that can be executed concurrently."""

    stage_index: int
    step_ids: Tuple[str, ...]
    estimated_ms: float = 100.0
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "stage_index": self.stage_index,
            "step_ids": list(self.step_ids),
            "estimated_ms": self.estimated_ms,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_index": self.stage_index,
            "step_ids": list(self.step_ids),
            "estimated_ms": self.estimated_ms,
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Complete multi-stage execution plan derived from a WorkflowManifest."""

    workflow_id: str
    stages: Tuple[ExecutionStage, ...]
    critical_path: Tuple[str, ...]
    total_estimated_ms: float
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "workflow_id": self.workflow_id,
            "stages": [s.to_dict() for s in self.stages],
            "critical_path": list(self.critical_path),
            "total_estimated_ms": self.total_estimated_ms,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "stages": [s.to_dict() for s in self.stages],
            "critical_path": list(self.critical_path),
            "total_estimated_ms": self.total_estimated_ms,
            "checksum": self.checksum,
        }


class ExecutionPlanner:
    """Converts WorkflowManifest DAGs into topologically sorted ExecutionPlans."""

    def create_plan(self, manifest: WorkflowManifest) -> ExecutionPlan:
        # Build dependency graph
        deps: dict[str, set[str]] = {}
        for s in manifest.step_definitions:
            deps[s.step_id] = set(s.dependencies)

        stages: List[ExecutionStage] = []
        completed: set[str] = set()
        stage_idx = 0

        while len(completed) < len(manifest.step_definitions):
            ready = [
                sid for sid, d in deps.items()
                if sid not in completed and d.issubset(completed)
            ]
            if not ready:
                raise ValueError("Cyclic dependency detected in WorkflowManifest DAG!")

            ready.sort()
            stage = ExecutionStage(stage_index=stage_idx, step_ids=tuple(ready))
            stages.append(stage)
            completed.update(ready)
            stage_idx += 1

        # Calculate critical path
        critical_path = tuple(s.step_id for s in manifest.step_definitions)
        total_estimated = float(len(stages) * 100)

        return ExecutionPlan(
            workflow_id=manifest.metadata.workflow_id,
            stages=tuple(stages),
            critical_path=critical_path,
            total_estimated_ms=total_estimated,
        )
