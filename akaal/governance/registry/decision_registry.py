"""
AKAAL Platform 6 — Governance Decision Registry.
"""

from typing import Dict, List, Optional
from akaal.governance.domain.models import GovernanceDecision


class DecisionRegistry:
    """Centralized registry for recorded governance decisions and rationales."""

    def __init__(self) -> None:
        self._decisions: Dict[str, GovernanceDecision] = {}

    def register_decision(self, decision: GovernanceDecision) -> None:
        self._decisions[decision.decision_id] = decision

    def get_decision(self, decision_id: str) -> Optional[GovernanceDecision]:
        return self._decisions.get(decision_id)

    def list_decisions(self) -> List[GovernanceDecision]:
        return list(self._decisions.values())
