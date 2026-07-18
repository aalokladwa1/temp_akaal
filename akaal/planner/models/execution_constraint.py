"""
Akaal — First-Class Execution Constraint Model
==============================================
First-class planning object defining parallelism, worker, resource, and window constraints.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionConstraints:
    max_parallelism: int = 8
    max_workers: int = 16
    cpu_limit_cores: float = 16.0
    memory_limit_gb: float = 32.0
    network_limit_mbps: float = 1000.0
    business_blackout_windows: List[Dict[str, Any]] = field(default_factory=list)
    dependency_locks: List[str] = field(default_factory=list)
    validation_gates_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_parallelism": self.max_parallelism,
            "max_workers": self.max_workers,
            "cpu_limit_cores": self.cpu_limit_cores,
            "memory_limit_gb": self.memory_limit_gb,
            "network_limit_mbps": self.network_limit_mbps,
            "business_blackout_windows": self.business_blackout_windows,
            "dependency_locks": self.dependency_locks,
            "validation_gates_required": self.validation_gates_required,
        }
