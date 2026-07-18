"""
Akaal — Resource Allocation Graph
=================================
Graph model performing logical allocation connecting ExecutionTasks to logical workers and infrastructure.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ResourceAllocationGraph:
    task_allocations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    worker_assignments: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    def allocate_task(self, task_id: str, worker_id: str, cpu: float, memory_gb: float) -> None:
        self.task_allocations[task_id] = {
            "worker_id": worker_id,
            "allocated_cpu": cpu,
            "allocated_memory_gb": memory_gb,
        }
        self.worker_assignments[worker_id].append(task_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_allocations": self.task_allocations,
            "worker_assignments": dict(self.worker_assignments),
        }
