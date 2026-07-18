"""
Akaal — Simulation Report Model
===============================
Output report document from SimulationEngine dry-run evaluations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.rulebook.models.rule_execution_trace import RuleExecutionTrace


@dataclass
class SimulationReport:
    """Read-only dry-run simulation summary."""
    rules_loaded: int = 0
    rules_applied: int = 0
    rules_skipped: int = 0
    rules_overridden: int = 0
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    policy_overrides: List[Dict[str, Any]] = field(default_factory=list)
    resolution_timeline: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_order: List[str] = field(default_factory=list)
    dependency_graph_summary: Dict[str, Any] = field(default_factory=dict)
    estimated_complexity: str = "LOW"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    capability_validation: Dict[str, Any] = field(default_factory=dict)
    execution_trace: Optional[RuleExecutionTrace] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules_loaded": self.rules_loaded,
            "rules_applied": self.rules_applied,
            "rules_skipped": self.rules_skipped,
            "rules_overridden": self.rules_overridden,
            "conflicts": self.conflicts,
            "warnings": self.warnings,
            "policy_overrides": self.policy_overrides,
            "resolution_timeline": self.resolution_timeline,
            "evaluation_order": self.evaluation_order,
            "dependency_graph_summary": self.dependency_graph_summary,
            "estimated_complexity": self.estimated_complexity,
            "capability_validation": self.capability_validation,
            "execution_trace": self.execution_trace.to_dict() if self.execution_trace else {},
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
