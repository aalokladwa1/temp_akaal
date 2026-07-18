"""
Akaal — Resource Schedule Model
================================
Logical resource scheduling model. Planner allocates resources logically only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WorkerAllocation:
    worker_id: str
    assigned_task_ids: List[str] = field(default_factory=list)
    allocated_cpu: float = 2.0
    allocated_memory_gb: float = 4.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "assigned_task_ids": self.assigned_task_ids,
            "allocated_cpu": self.allocated_cpu,
            "allocated_memory_gb": self.allocated_memory_gb,
        }


@dataclass
class ResourceSchedule:
    workers: List[WorkerAllocation] = field(default_factory=list)
    total_cpu_allocated: float = 0.0
    total_memory_allocated_gb: float = 0.0
    total_disk_allocated_gb: float = 0.0
    network_mbps_allocated: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workers": [w.to_dict() for w in self.workers],
            "total_cpu_allocated": round(self.total_cpu_allocated, 2),
            "total_memory_allocated_gb": round(self.total_memory_allocated_gb, 2),
            "total_disk_allocated_gb": round(self.total_disk_allocated_gb, 2),
            "network_mbps_allocated": round(self.network_mbps_allocated, 2),
        }
