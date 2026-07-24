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
