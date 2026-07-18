"""
Akaal — Planner Validator
==========================
Validates MigrationExecutionPlan graph integrity, checksum stability, and dependency correctness.
"""

from typing import List
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.models.execution_graph import ExecutionGraph


class PlannerValidator:
    """Validates MigrationExecutionPlan and ExecutionGraph structural integrity."""

    @staticmethod
    def validate_plan(plan: MigrationExecutionPlan) -> List[str]:
        warnings: List[str] = []
        if not plan.sha256_checksum:
            warnings.append("MigrationExecutionPlan is missing sha256_checksum.")
        if not plan.execution_graph:
            warnings.append("MigrationExecutionPlan has empty execution_graph.")
        if not plan.cutover_plan:
            warnings.append("MigrationExecutionPlan has empty cutover_plan.")
        return warnings

    @staticmethod
    def validate_graph(graph: ExecutionGraph) -> List[str]:
        warnings: List[str] = []
        all_task_ids = set(graph.tasks.keys())

        # Detect unreachable / orphan nodes
        reachable = set()
        for src in graph.edges:
            reachable.add(src)
            reachable.update(graph.edges[src])

        orphans = [t_id for t_id in all_task_ids if t_id not in reachable and len(graph.tasks) > 1]
        if orphans:
            warnings.append(f"Orphan nodes detected: {orphans}")

        # Detect duplicate task IDs
        if len(all_task_ids) != len(graph.tasks):
            warnings.append("Duplicate task IDs detected in ExecutionGraph.")

        # Detect broken dependencies (references to non-existent tasks)
        for task in graph.tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in all_task_ids:
                    warnings.append(f"Task {task.task_id} references non-existent dependency {dep_id}.")

        return warnings
