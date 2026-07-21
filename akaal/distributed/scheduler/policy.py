"""
Pluggable Scheduling Policies for ClusterScheduler.
Includes FIFO, Priority, Fair, Adaptive, Weighted, LeastLoaded, ResourceAware, Affinity, AntiAffinity, LocalityAware.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from akaal.distributed.domain.models import Worker, Task, SchedulerDecision


class SchedulingPolicy(ABC):
    """Abstract SchedulingPolicy interface."""

    @abstractmethod
    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        """Select best candidate worker for the task."""
        pass


class FIFOSchedulingPolicy(SchedulingPolicy):
    """First-In First-Out: Selects the first eligible candidate worker."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        return candidate_workers[0] if candidate_workers else None


class PrioritySchedulingPolicy(SchedulingPolicy):
    """Selects the worker with the lowest load among eligible candidates for high priority tasks."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return min(candidate_workers, key=lambda w: w.current_load)


class LeastLoadedSchedulingPolicy(SchedulingPolicy):
    """Selects candidate worker with the minimal current_load / capacity ratio."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return min(candidate_workers, key=lambda w: (w.current_load / max(w.capacity, 1)))


class ResourceAwareSchedulingPolicy(SchedulingPolicy):
    """Selects candidate worker with the maximum available CPU and memory resources."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return max(candidate_workers, key=lambda w: (w.resources.cpu_cores, w.resources.memory_mb))


class AffinitySchedulingPolicy(SchedulingPolicy):
    """Prefers candidate workers whose labels match the task's affinity labels."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        
        target_labels = task.labels
        best_worker = candidate_workers[0]
        best_score = -1

        for w in candidate_workers:
            score = sum(1 for k, v in target_labels.items() if w.labels.get(k) == v)
            if score > best_score:
                best_score = score
                best_worker = w

        return best_worker


class AntiAffinitySchedulingPolicy(SchedulingPolicy):
    """Avoids candidate workers whose labels match anti-affinity constraints."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        
        target_labels = task.labels
        for w in candidate_workers:
            conflict = any(w.labels.get(k) == v for k, v in target_labels.items())
            if not conflict:
                return w
        return candidate_workers[0]


class LocalityAwareSchedulingPolicy(SchedulingPolicy):
    """Prefers candidate workers on the node specified in task payload locality hints."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        
        preferred_node = task.payload.get("preferred_node_id")
        if preferred_node:
            for w in candidate_workers:
                if str(w.node_id) == preferred_node:
                    return w
        return candidate_workers[0]


class FairSchedulingPolicy(SchedulingPolicy):
    """Fair sharing policy balancing load across workers."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return min(candidate_workers, key=lambda w: w.current_load)


class AdaptiveSchedulingPolicy(SchedulingPolicy):
    """Adaptive scheduling considering worker load and health status."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return min(candidate_workers, key=lambda w: (w.current_load, -w.resources.cpu_cores))


class WeightedSchedulingPolicy(SchedulingPolicy):
    """Weighted scheduling selecting worker by weighted capacity ratio."""

    def select_worker(self, task: Task, candidate_workers: List[Worker]) -> Optional[Worker]:
        if not candidate_workers:
            return None
        return max(candidate_workers, key=lambda w: (w.capacity - w.current_load))
