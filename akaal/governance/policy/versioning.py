"""
AKAAL Platform 6 — Policy Versioning Manager.
"""

from typing import Dict, List, Optional
from akaal.governance.domain.models import EnterprisePolicy


class PolicyVersionManager:
    """Maintains policy version history, rollbacks, and changelogs."""

    def __init__(self) -> None:
        # Maps policy_id -> List of historical versions
        self._history: Dict[str, List[EnterprisePolicy]] = {}

    def record_version(self, policy: EnterprisePolicy) -> None:
        if policy.policy_id not in self._history:
            self._history[policy.policy_id] = []
        self._history[policy.policy_id].append(policy)

    def get_version_history(self, policy_id: str) -> List[EnterprisePolicy]:
        return self._history.get(policy_id, [])

    def rollback(self, policy_id: str, target_version: str) -> Optional[EnterprisePolicy]:
        history = self.get_version_history(policy_id)
        for p in reversed(history):
            if p.version == target_version:
                return p
        return None
