"""
AKAAL Platform 6 — Enterprise Policy Lifecycle Manager.
"""

from typing import Dict, Optional, List
import datetime

from akaal.governance.domain.models import EnterprisePolicy
from akaal.governance.domain.enums import PolicyCategory, RiskLevel, LifecycleState
from akaal.governance.domain.exceptions import PolicyViolationError


class PolicyLifecycleService:
    """Manages organization-wide governance policy creation and activation."""

    def __init__(self) -> None:
        self._policies: Dict[str, EnterprisePolicy] = {}

    def register_policy(self, policy: EnterprisePolicy) -> EnterprisePolicy:
        self._policies[policy.policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[EnterprisePolicy]:
        return self._policies.get(policy_id)

    def list_policies(self, category: Optional[PolicyCategory] = None) -> List[EnterprisePolicy]:
        if category:
            return [p for p in self._policies.values() if p.category == category]
        return list(self._policies.values())
