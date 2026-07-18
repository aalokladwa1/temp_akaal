"""
Akaal — Rule Evaluation Result Model
====================================
Tracks decision outcomes for individual rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from akaal.rulebook.models.rule import RuleProvenance


@dataclass
class RuleEvaluationResult:
    rule_id: str
    rule_name: str
    category: str
    status: str  # "APPLIED", "SKIPPED", "OVERRIDDEN", "REJECTED"
    scope: str = "GLOBAL"
    provenance: str = "VENDOR_PACK"
    rationale: str = ""
    action_payload: Dict[str, Any] = field(default_factory=dict)
    override_rule_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category,
            "status": self.status,
            "scope": self.scope,
            "provenance": self.provenance,
            "rationale": self.rationale,
            "action_payload": self.action_payload,
            "override_rule_id": self.override_rule_id,
            "timestamp": self.timestamp,
        }
