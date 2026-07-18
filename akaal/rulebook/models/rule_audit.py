"""
Akaal — Rule Audit Model
========================
Audit trail model for Rulebook decisions, overrides, and evaluation outcomes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class RuleAuditEntry:
    rule_id: str
    decision: str  # "APPLIED", "SKIPPED", "OVERRIDDEN", "REJECTED"
    scope: str
    provenance: str
    rationale: str
    override_rule_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "decision": self.decision,
            "scope": self.scope,
            "provenance": self.provenance,
            "rationale": self.rationale,
            "override_rule_id": self.override_rule_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RuleAudit:
    correlation_id: str
    entries: List[RuleAuditEntry] = field(default_factory=list)

    def add_entry(self, entry: RuleAuditEntry) -> None:
        self.entries.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "entries": [e.to_dict() for e in self.entries],
        }
