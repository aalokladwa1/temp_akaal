"""
akaalEngine.runtime.models.resource
===================================
Canonical resource budgets, requirements, snapshots, and admission policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ResourceRequirement:
    """Resource requirement for task admission."""
    cpu_cores: float = 1.0
    memory_mb: float = 512.0
    concurrency_slots: int = 1
    weight: int = 1


@dataclass(frozen=True)
class ResourceSnapshot:
    """Snapshot of measured system & worker resources."""
    cpu_percent: float = 0.0
    memory_utilization_pct: float = 0.0
    allocated_cpu_cores: float = 0.0
    allocated_memory_mb: float = 0.0
    active_worker_slots: int = 0
    max_worker_slots: int = 100
    queue_depth: int = 0


@dataclass(frozen=True)
class ResourceBudget:
    """Runtime capacity budget constraints."""
    max_worker_slots: int = 64
    max_cpu_cores: float = 16.0
    max_memory_mb: float = 32768.0
    max_queue_depth: int = 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_worker_slots": self.max_worker_slots,
            "max_cpu_cores": self.max_cpu_cores,
            "max_memory_mb": self.max_memory_mb,
            "max_queue_depth": self.max_queue_depth,
        }


@dataclass(frozen=True)
class ResourceAdmissionPolicy:
    """Policy rules for task admission into Runtime."""
    max_cpu_threshold_pct: float = 90.0
    max_memory_threshold_pct: float = 90.0
    allow_oversubscription: bool = False
    oversubscription_factor: float = 1.2
