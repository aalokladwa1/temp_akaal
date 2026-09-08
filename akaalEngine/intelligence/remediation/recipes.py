"""akaalEngine.intelligence.remediation.recipes
==================================================
Typed, deterministic remediation recipes. Each recipe names a real,
already-existing canonical action_type (registered in
akaalEngine.intelligence.mediation.autonomy.ACTION_AUTONOMY_REGISTRY) that a
REAL canonical command handler can execute AFTER mediation/approval -- never
an invented capability. `select_recipe` is a pure function: given an RCA
primary-hypothesis label and bottleneck classification, it returns AT MOST one
matching recipe, or None if no canonical action applies (in which case the
producer must recommend escalation, never fabricate an action).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from akaalEngine.intelligence.mediation.proposal import RiskClassification


@dataclass(frozen=True)
class RemediationRecipe:
    recipe_id: str
    action_type: str
    trigger_description: str
    risk: RiskClassification
    requires_approval: bool
    reversibility_note: str
    verification_note: str

    def to_dict(self) -> dict:
        return {
            "recipe_id": self.recipe_id,
            "action_type": self.action_type,
            "trigger_description": self.trigger_description,
            "risk": self.risk.value,
            "requires_approval": self.requires_approval,
            "reversibility_note": self.reversibility_note,
            "verification_note": self.verification_note,
        }


_PAUSE_FOR_CDC_CATCHUP = RemediationRecipe(
    recipe_id="pause-for-cdc-catchup",
    action_type="propose_remediation_pause_migration",
    trigger_description="CDC apply-side backlog growth with stable source transport (apply-bound saturation hypothesis).",
    risk=RiskClassification.MEDIUM,
    requires_approval=True,
    reversibility_note="Fully reversible via the existing canonical resume_migration command once the backlog stabilizes.",
    verification_note="Verify via a subsequent P7C.13/P7C.14 request that CDC backlog growth has stopped before resuming.",
)


def select_recipe(*, primary_hypothesis_label: str, fabric_status: str, validation_status: str) -> Optional[RemediationRecipe]:
    """Deterministic, explicit rule matching -- never a fallback that
    fabricates an action for an unmatched cause. Governance-critical causes
    (FABRIC/VALIDATION) have NO automated recipe here: ownership/lease and
    validation failures are not something a pause/resume action can fix, and
    this module never invents an action beyond what canonical runtime
    genuinely supports."""
    if fabric_status == "CRITICAL" or validation_status == "CRITICAL":
        return None
    if "apply is falling behind" in primary_hypothesis_label:
        return _PAUSE_FOR_CDC_CATCHUP
    return None
