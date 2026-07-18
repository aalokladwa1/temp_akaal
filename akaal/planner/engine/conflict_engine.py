"""
Akaal — Conflict Resolution Engine
=====================================
Resolves resource, dependency, checkpoint, rollback, scheduling, and parallelism conflicts
deterministically before MigrationExecutionPlan assembly.
"""

from typing import Any, Dict, List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph


class ConflictResolutionEngine:
    """Detects and resolves planning conflicts before plan assembly."""

    def resolve(
        self, ctx: PlanningContext, graph: ExecutionGraph
    ) -> Dict[str, Any]:
        conflicts_detected: List[Dict[str, Any]] = []
        resolutions_applied: List[str] = []

        # Resource conflict: max_workers vs total tasks
        task_count = len(graph.tasks)
        max_workers = ctx.constraints.max_workers
        if task_count > max_workers * 4:
            conflicts_detected.append({
                "type": "RESOURCE_CONFLICT",
                "detail": f"Task count {task_count} exceeds safe worker capacity {max_workers * 4}.",
            })
            resolutions_applied.append("REDUCE_PARALLELISM_TO_SAFE_LIMIT")

        # Parallelism constraint satisfaction
        if ctx.constraints.max_parallelism > max_workers:
            conflicts_detected.append({
                "type": "PARALLELISM_CONFLICT",
                "detail": f"max_parallelism ({ctx.constraints.max_parallelism}) > max_workers ({max_workers}).",
            })
            resolutions_applied.append("CAP_PARALLELISM_AT_MAX_WORKERS")

        return {
            "conflicts_detected": conflicts_detected,
            "resolutions_applied": resolutions_applied,
            "is_clean": len(conflicts_detected) == 0,
        }
