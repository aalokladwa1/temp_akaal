"""
Akaal — Execution Sequence Model
================================
Deterministic execution sequence ordering.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ExecutionSequence:
    ordered_task_ids: List[str] = field(default_factory=list)
    parallel_batches: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ordered_task_ids": self.ordered_task_ids,
            "parallel_batches": self.parallel_batches,
        }
