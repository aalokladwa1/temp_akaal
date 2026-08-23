"""
akaalEngine.runtime.resources.admission
========================================
Resource admission controller evaluating CPU, memory, slot capacity, and task weight.
"""

from threading import RLock
from typing import Dict, Optional, Tuple

from akaalEngine.runtime.models.errors import ResourceAdmissionError
from akaalEngine.runtime.models.resource import (
    ResourceAdmissionPolicy,
    ResourceBudget,
    ResourceRequirement,
)


class ResourceAdmissionController:
    """
    ResourceAdmissionController tracking capacity usage and admitting or rejecting work based on policy.
    """

    def __init__(
        self,
        budget: Optional[ResourceBudget] = None,
        policy: Optional[ResourceAdmissionPolicy] = None,
    ) -> None:
        self.budget = budget or ResourceBudget()
        self.policy = policy or ResourceAdmissionPolicy()
        self._lock = RLock()
        self._allocated_cpu: float = 0.0
        self._allocated_memory_mb: float = 0.0
        self._allocated_slots: int = 0

    def evaluate_admission(self, req: ResourceRequirement) -> Tuple[bool, Optional[str]]:
        """Evaluates whether a task requirement can be admitted under current budget and policy."""
        with self._lock:
            if (self._allocated_slots + req.concurrency_slots) > self.budget.max_worker_slots:
                return False, f"Worker slots exhausted ({self._allocated_slots}/{self.budget.max_worker_slots})"

            if not self.policy.allow_oversubscription:
                if (self._allocated_cpu + req.cpu_cores) > self.budget.max_cpu_cores:
                    return False, f"CPU budget exceeded ({self._allocated_cpu:.1f}/{self.budget.max_cpu_cores:.1f})"
                if (self._allocated_memory_mb + req.memory_mb) > self.budget.max_memory_mb:
                    return False, f"Memory budget exceeded ({self._allocated_memory_mb:.1f}/{self.budget.max_memory_mb:.1f} MB)"

            return True, None

    def allocate(self, req: ResourceRequirement) -> None:
        with self._lock:
            can_admit, reason = self.evaluate_admission(req)
            if not can_admit:
                raise ResourceAdmissionError(reason or "Admission denied")
            self._allocated_cpu += req.cpu_cores
            self._allocated_memory_mb += req.memory_mb
            self._allocated_slots += req.concurrency_slots

    def release(self, req: ResourceRequirement) -> None:
        with self._lock:
            self._allocated_cpu = max(0.0, self._allocated_cpu - req.cpu_cores)
            self._allocated_memory_mb = max(0.0, self._allocated_memory_mb - req.memory_mb)
            self._allocated_slots = max(0, self._allocated_slots - req.concurrency_slots)

    def get_utilization(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "allocated_cpu": self._allocated_cpu,
                "allocated_memory_mb": self._allocated_memory_mb,
                "allocated_slots": self._allocated_slots,
                "max_slots": self.budget.max_worker_slots,
                "max_cpu": self.budget.max_cpu_cores,
                "max_memory_mb": self.budget.max_memory_mb,
            }
