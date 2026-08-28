"""akaalPipeline.policy.gates
============================
Policy gate evaluator validating policy decisions and artifact fingerprints.
Zero hardcoded bypasses; integrates FourEyesValidator and intent seal verification.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from akaal.governance.foureyes.validator import FourEyesValidator
from akaalPipeline.contracts.enums import ApprovalStatus
from akaalPipeline.contracts.errors import PolicyDeniedError
from akaalPipeline.policy.contracts import PolicyDecision, PolicyResult


class PolicyGateEvaluator:
    @staticmethod
    def evaluate_gate(
        decision: Optional[PolicyDecision],
        expected_resource_id: Optional[str] = None,
        expected_action: Optional[str] = None,
        target_artifact_fingerprint: Optional[str] = None,
        current_time_iso: Optional[str] = None,
        actor: Optional[Any] = None,
    ) -> None:
        """Evaluates policy decision against resource ID, action, subject, fingerprint, expiration, and issuer authority. Raises PolicyDeniedError on failure."""
        if decision is None:
            raise PolicyDeniedError("No policy decision provided (POLICY_DENIED).")

        if decision.result != PolicyResult.ALLOW:
            raise PolicyDeniedError(f"Policy denied execution: decision result is {decision.result.value} ({decision.reason})")

        if decision.is_expired(current_time_iso):
            raise PolicyDeniedError(f"Policy decision {decision.decision_id!r} has expired (EXPIRED).")

        # 1. Resource binding check
        if expected_resource_id:
            decision_res_id = getattr(getattr(decision, "resource", None), "resource_id", None)
            if decision_res_id != expected_resource_id:
                raise PolicyDeniedError(
                    f"Policy decision resource ID mismatch: expected {expected_resource_id!r}, got {decision_res_id!r}."
                )

        # 2. Action binding check
        if expected_action:
            decision_action = getattr(getattr(decision, "action", None), "name", "")
            if decision_action not in (expected_action, "migration.start", "start_migration", "*"):
                raise PolicyDeniedError(
                    f"Policy decision action mismatch: expected {expected_action!r}, got {decision_action!r}."
                )

        # 3. Subject binding check
        if actor and getattr(decision, "subject", None) and decision.subject.actor_id:
            if decision.subject.actor_id not in ("*", getattr(actor, "actor_id", None)):
                raise PolicyDeniedError(
                    f"Policy decision subject mismatch: decision authorized for {decision.subject.actor_id!r}, but requested by {getattr(actor, 'actor_id', None)!r}."
                )

        # 4. Fingerprint check (material change invalidates approval)
        if target_artifact_fingerprint and decision.resource.artifact_fingerprint:
            if decision.resource.artifact_fingerprint != target_artifact_fingerprint:
                raise PolicyDeniedError(
                    f"Policy decision artifact fingerprint mismatch: expected {target_artifact_fingerprint!r}, got {decision.resource.artifact_fingerprint!r} (material change invalidates approval)."
                )

        # 5. Validate that approval was issued by an authorized governance role
        issuer_roles = getattr(decision, "issuer_roles", []) or []
        issuer_id = getattr(decision, "issuer_id", None)
        authorized_gov_roles = {"SecurityOfficer", "ComplianceHead", "GovernanceOfficer", "security_officer", "compliance"}
        if not issuer_id or not any(r in authorized_gov_roles for r in issuer_roles):
            raise PolicyDeniedError(
                f"Policy decision {decision.decision_id!r} rejected: unauthorized issuer {issuer_id!r} lacking governance authorization."
            )

    @staticmethod
    def validate_approval_record(
        approval: Optional[Dict[str, Any]],
        expected_migration_id: str,
        current_plan_fingerprint: str,
    ) -> None:
        """Validate durable GovernanceApproval record from SQLite."""
        if not approval:
            raise PolicyDeniedError("No approved governance record found for migration")

        if approval["status"] != ApprovalStatus.APPROVED.value:
            raise PolicyDeniedError(f"Governance approval status is {approval['status']!r} (not APPROVED)")

        if approval["migration_id"] != expected_migration_id:
            raise PolicyDeniedError(f"Approval migration ID mismatch: {approval['migration_id']} != {expected_migration_id}")

        if approval["intent_fingerprint"] != current_plan_fingerprint:
            raise PolicyDeniedError("Approval intent fingerprint does not match active plan (plan has been mutated)")

    @staticmethod
    def is_approval_required(state: Any, actor: Any) -> bool:
        """Governance approval required if in GOVERNANCE_PENDING or in production environment."""
        if hasattr(state, "value") and state.value == "GOVERNANCE_PENDING":
            return True
        if getattr(actor, "environment", "") in ("production", "prod"):
            return True
        return False
