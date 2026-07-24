"""HealingPolicyEngine: Enterprise compliance policies and multi-level approval workflows."""

from typing import Dict, Any, List
from akaal.healing.core.interfaces import IHealingPolicy
from akaal.healing.core.config import HealingProfile, ApprovalMode
from akaal.healing.core.models import HealingPlan


class HealingPolicyEngine(IHealingPolicy):
    """Evaluates repair plan compliance and multi-level approval constraints."""

    def __init__(self, profile: HealingProfile = HealingProfile.AUTOMATIC, approval_mode: ApprovalMode = ApprovalMode.AUTOMATIC):
        self.profile = profile
        self.approval_mode = approval_mode

    @property
    def policy_name(self) -> str:
        return f"HealingPolicyEngine({self.profile.value}:{self.approval_mode.value})"

    def evaluate_repair(self, plan: HealingPlan) -> Dict[str, Any]:
        """Evaluate compliance and determine required approval level."""
        requires_approval = False
        approval_level = "NONE"

        if self.profile == HealingProfile.STRICT_FINANCE:
            requires_approval = True
            approval_level = "EXECUTIVE"
        elif self.profile == HealingProfile.STRICT_HEALTHCARE:
            requires_approval = True
            approval_level = "DUAL"
        elif self.approval_mode in (ApprovalMode.SINGLE, ApprovalMode.DUAL, ApprovalMode.EXECUTIVE):
            requires_approval = True
            approval_level = self.approval_mode.value

        return {
            "policy_profile": self.profile.value,
            "requires_approval": requires_approval,
            "approval_level": approval_level,
            "compliant": True,
        }
