"""
Akaal — Planning Decision Model
===============================
Immutable record explaining major planning decisions made by Planner Platform.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class PlanningDecision:
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: str = "STAGE_SEQUENCING"
    reason: str = ""
    evidence_references: List[str] = field(default_factory=list)
    risk_references: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    confidence_score: float = 100.0
    strategy_id: str = "strat_default"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "reason": self.reason,
            "evidence_references": self.evidence_references,
            "risk_references": self.risk_references,
            "dependencies": self.dependencies,
            "confidence_score": self.confidence_score,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
        }
