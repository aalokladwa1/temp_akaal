"""Worker Allocator and Worker Selection Policy Engine."""

import threading
from typing import List, Optional
from akaal.workflow.queues.interfaces import StepExecutionTask
from akaal.workflow.workers.registry import WorkerNode, WorkerRegistry


class WorkerAllocator:
    """Allocates worker nodes for ready step execution tasks using least-loaded selection."""

    def __init__(self, registry: WorkerRegistry) -> None:
        self._registry = registry
        self._lock = threading.Lock()

    def select_worker(self, task: StepExecutionTask) -> Optional[WorkerNode]:
        """Select optimal healthy worker node for a step execution task."""
        with self._lock:
            healthy = self._registry.list_healthy_workers()
            if not healthy:
                return None
            # Least loaded worker selection policy
            sorted_workers = sorted(healthy, key=lambda w: w.active_tasks_count)
            return sorted_workers[0]
