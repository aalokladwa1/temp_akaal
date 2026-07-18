"""
Akaal — Planner Diagnostic Model
==================================
Structured diagnostic model for Planner Platform warnings and validation telemetry.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PlannerDiagnostic:
    diagnostic_id: str
    severity: str  # "INFO", "WARNING", "ERROR", "CRITICAL"
    category: str
    affected_task_ids: List[str] = field(default_factory=list)
    root_cause: str = ""
    recommended_resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "severity": self.severity,
            "category": self.category,
            "affected_task_ids": self.affected_task_ids,
            "root_cause": self.root_cause,
            "recommended_resolution": self.recommended_resolution,
        }
