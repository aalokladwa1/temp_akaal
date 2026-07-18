"""
Akaal — Execution Graph Model
=============================
Graph connecting ExecutionTasks and inter-task dependencies.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from akaal.planner.models.execution_task import ExecutionTask


@dataclass
class ExecutionGraph:
    """Execution Graph connecting ExecutionTask nodes."""
    tasks: Dict[str, ExecutionTask] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    reverse_edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    def add_task(self, task: ExecutionTask) -> None:
        self.tasks[task.task_id] = task
        for dep_id in task.dependencies:
            self.add_edge(dep_id, task.task_id)

    def add_edge(self, source_id: str, target_id: str) -> None:
        self.edges[source_id].append(target_id)
        self.reverse_edges[target_id].append(source_id)

    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        return self.tasks.get(task_id)

    def topological_sort(self) -> List[ExecutionTask]:
        in_degree = {t_id: 0 for t_id in self.tasks}
        for src, targets in self.edges.items():
            for t in targets:
                if t in in_degree:
                    in_degree[t] += 1

        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        sorted_tasks: List[ExecutionTask] = []

        while queue:
            curr = queue.popleft()
            if curr in self.tasks:
                sorted_tasks.append(self.tasks[curr])
            for neighbor in self.edges.get(curr, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        if len(sorted_tasks) != len(self.tasks):
            return list(self.tasks.values())

        return sorted_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self.tasks),
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "edges": dict(self.edges),
        }
