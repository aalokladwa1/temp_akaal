"""
Akaal — Parallel Execution Engine
====================================
Determines independent execution groups, safe parallelism, synchronization barriers.
Planner never executes workers.
"""

from typing import Any, Dict, List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.execution_sequence import ExecutionSequence


class ParallelEngine:
    """Determines safe parallel execution strategy."""

    def build_parallel_strategy(
        self, ctx: PlanningContext, graph: ExecutionGraph, sequence: ExecutionSequence
    ) -> Dict[str, Any]:
        safe_parallelism = ctx.constraints.max_parallelism
        max_workers = ctx.constraints.max_workers

        parallel_groups: Dict[str, List[str]] = {}
        for task_id in sequence.ordered_task_ids:
            task = graph.get_task(task_id)
            if task and task.stage_id:
                parallel_groups.setdefault(task.stage_id, []).append(task_id)

        synchronization_barriers = list(parallel_groups.keys())

        return {
            "safe_parallelism": safe_parallelism,
            "max_workers": max_workers,
            "parallel_groups": {k: v for k, v in parallel_groups.items()},
            "synchronization_barriers": synchronization_barriers,
        }
