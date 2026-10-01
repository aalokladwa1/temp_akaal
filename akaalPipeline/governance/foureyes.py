"""
akaalPipeline.governance.foureyes
=================================
Canonical Four-Eyes / Maker-Checker enforcement authority for akaalPipeline.
Enforces the invariant that an actor who proposes/requests a mutation or elevated
privilege cannot approve or execute that mutation themselves.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode, PolicyDeniedError


class FourEyesValidator:
    """Validator implementing four-eyes principle rules."""

    def validate_action(
        self,
        requester_id: str,
        approver_id: str,
        action_type: str = "GENERIC_MUTATION",
    ) -> Tuple[bool, str]:
        """Validates that approver_id is distinct from requester_id.

        Returns (True, "OK") or (False, rejection_reason).
        """
        if not approver_id or not str(approver_id).strip():
            return False, "Approver ID cannot be empty or unspecified."

        if not requester_id or not str(requester_id).strip():
            return False, "Requester ID cannot be empty or unspecified."

        if str(requester_id).strip().lower() == str(approver_id).strip().lower():
            return (
                False,
                f"Self-approval violation: Requester '{requester_id}' cannot approve their own '{action_type}' request under the Four-Eyes principle.",
            )

        return True, "Four-Eyes validation succeeded."

    def validate_quorum(
        self,
        requester_id: str,
        approver_ids: Sequence[str],
        min_quorum: int = 1,
        action_type: str = "GENERIC_MUTATION",
    ) -> Tuple[bool, str]:
        """Validates that quorum requirements are satisfied with distinct non-requester approvers."""
        clean_requester = str(requester_id).strip().lower() if requester_id else ""
        valid_approvers = set()

        for app in approver_ids:
            clean_app = str(app).strip()
            if not clean_app:
                continue
            if clean_app.lower() == clean_requester:
                return (
                    False,
                    f"Self-approval violation: Requester '{requester_id}' cannot be in the approver quorum for '{action_type}'.",
                )
            valid_approvers.add(clean_app.lower())

        if len(valid_approvers) < min_quorum:
            return (
                False,
                f"Quorum violation: required {min_quorum} distinct non-requester approver(s), but found {len(valid_approvers)}.",
            )

        return True, "Quorum validation succeeded."


class FourEyesEnforcer:
    """Enforcer raising PolicyDeniedError on any Four-Eyes violation."""

    def __init__(self, validator: Optional[FourEyesValidator] = None) -> None:
        self.validator = validator or FourEyesValidator()

    def enforce(
        self,
        requester_id: str,
        approver_id: str,
        action_type: str = "GENERIC_MUTATION",
    ) -> None:
        """Enforces single-approver maker-checker invariant. Raises PolicyDeniedError if violated."""
        ok, msg = self.validator.validate_action(requester_id, approver_id, action_type)
        if not ok:
            raise PolicyDeniedError(f"Four-Eyes Governance Denied: {msg}")

    def enforce_quorum(
        self,
        requester_id: str,
        approver_ids: Sequence[str],
        min_quorum: int = 1,
        action_type: str = "GENERIC_MUTATION",
    ) -> None:
        """Enforces quorum maker-checker invariant. Raises PolicyDeniedError if violated."""
        ok, msg = self.validator.validate_quorum(requester_id, approver_ids, min_quorum, action_type)
        if not ok:
            raise PolicyDeniedError(f"Four-Eyes Governance Denied: {msg}")
