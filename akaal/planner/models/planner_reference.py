"""
Akaal — Planner Reference Model
=================================
Identity and risk reference dataclasses for Planner Platform traceability.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PlannerReference:
    planner_ref_id: str
    task_id: str
    risk_item_id: Optional[str] = None
    canonical_object_id: Optional[str] = None
    object_type: str = "ExecutionTask"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planner_ref_id": self.planner_ref_id,
            "task_id": self.task_id,
            "risk_item_id": self.risk_item_id,
            "canonical_object_id": self.canonical_object_id,
            "object_type": self.object_type,
        }
