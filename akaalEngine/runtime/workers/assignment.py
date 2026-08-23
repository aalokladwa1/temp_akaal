"""
akaalEngine.runtime.workers.assignment
======================================
Deterministic Task Assignment Engine selecting best eligible worker by capability match and lowest slot load.
"""

import logging
from threading import RLock
from typing import Optional, Sequence

from akaalEngine.runtime.models.errors import WorkerNotFoundError
from akaalEngine.runtime.models.task import TaskSpec
from akaalEngine.runtime.models.worker import WorkerSnapshot
from akaalEngine.runtime.workers.registry import WorkerRegistry

logger = logging.getLogger("akaalEngine.runtime.workers.assignment")


class TaskAssignmentEngine:
    """
    Predictable, deterministic worker selection algorithm.
    """

    def __init__(self, registry: WorkerRegistry) -> None:
        self.registry = registry
        self._lock = RLock()

    def select_worker(self, spec: TaskSpec) -> WorkerSnapshot:
        with self._lock:
            candidates = self.registry.list_available_workers(spec.required_capabilities)
            if not candidates:
                from akaalEngine.runtime.models.errors import WorkerNotFoundError
                raise WorkerNotFoundError("No eligible available worker found matching required capabilities.")

            # Sort deterministically: lowest load ratio first, then node_id, then worker_id
            candidates.sort(key=lambda w: (w.active_task_count / float(w.max_concurrency_slots), w.node_id, w.worker_id))
            selected = candidates[0]
            logger.info(f"[TaskAssignmentEngine] Assigned task '{spec.task_id}' to worker '{selected.worker_id}'.")
            return selected
