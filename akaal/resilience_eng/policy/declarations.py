"""Declarative Policy Declarations and DeclarativePolicyEngine."""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class PolicyDeclaration:
    policy_id: str = "pol_001"
    max_blast_radius: str = "Service"
    require_approval: bool = True
    mandatory_checkpoint: bool = True
    max_rto_sec: float = 30.0
    max_rpo_sec: float = 5.0


class DeclarativePolicyEngine:
    """Enforces version-controlled declarative policies on resilience experiments."""

    def __init__(self, declaration: PolicyDeclaration = None):
        self.declaration = declaration or PolicyDeclaration()

    def validate_experiment_policy(self, scope: str, rto_sec: float) -> Dict[str, Any]:
        valid = rto_sec <= self.declaration.max_rto_sec
        return {
            "compliant": valid,
            "policy_id": self.declaration.policy_id,
            "max_blast_radius": self.declaration.max_blast_radius,
            "reason": "APPROVED" if valid else "EXCEEDS_RTO_LIMIT",
        }
