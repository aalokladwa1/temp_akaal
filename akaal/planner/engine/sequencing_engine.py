"""
Akaal — Sequencing Engine
==========================
Produces deterministic ExecutionSequence from topological sort of ExecutionGraph.
"""

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.execution_sequence import ExecutionSequence


class SequencingEngine:
    """Generates deterministic execution ordering from ExecutionGraph topology."""

    def build_sequence(self, ctx: PlanningContext, graph: ExecutionGraph) -> ExecutionSequence:
        sorted_tasks = graph.topological_sort()
        ordered_ids = [t.task_id for t in sorted_tasks]

        # Group into parallel batches by stage
        batches: dict = {}
        for task in sorted_tasks:
            batches.setdefault(task.stage_id, []).append(task.task_id)

        return ExecutionSequence(
            ordered_task_ids=ordered_ids,
            parallel_batches=list(batches.values()),
        )
