"""
AKAAL Platform 6 — Four-Eyes Dual Authorization Validator.
"""

from typing import List, Tuple
from akaal.governance.domain.exceptions import SoDViolationError


class FourEyesValidator:
    """Enforces dual independent sign-off requirements for high-risk operations."""

    def validate_four_eyes(self, primary_approver: str, secondary_approver: str) -> Tuple[bool, str]:
        if not primary_approver or not secondary_approver:
            return False, "Four-Eyes validation failed: Missing approver."
        if primary_approver == secondary_approver:
            return False, f"Four-Eyes validation failed: Primary approver '{primary_approver}' cannot act as secondary approver."
        return True, "Four-Eyes validation successful."

    def validate_action(self, requester_id: str, approver_id: str, action_type: str = "CUTOVER", secondary_approver: str = "") -> Tuple[bool, str]:
        """Validate that maker and checker are distinct principals."""
        if requester_id == approver_id:
            return False, f"Four-Eyes validation failed: Requester '{requester_id}' cannot self-approve action '{action_type}'."
        if secondary_approver and (approver_id == secondary_approver or requester_id == secondary_approver):
            return False, f"Four-Eyes validation failed: Non-distinct approvers for '{action_type}'."
        return True, "Four-Eyes validation successful."
