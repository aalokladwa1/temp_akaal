"""akaalPipeline.policy.four_eyes
================================
Canonical Native Four-Eyes / Maker-Checker Validator.
Enforces strict dual-control separation of duties.
"""

from __future__ import annotations
from typing import Tuple, Optional, List


class FourEyesValidator:
    """Canonical Four-Eyes (Maker-Checker) Validator."""

    def validate_action(
        self,
        requester_id: str,
        approver_id: str,
        action_type: str = "GENERIC_APPROVAL",
    ) -> Tuple[bool, str]:
        if not requester_id or not approver_id:
            return False, "Requester and approver IDs must be non-empty."
        if requester_id == approver_id:
            return False, f"Four-Eyes Violation: Requester '{requester_id}' cannot self-approve action '{action_type}'."
        return True, "Four-Eyes validation passed."

    validate_approval = validate_action
