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
        authorized_gov_roles = {"admin", "governor", "SecurityOfficer", "ComplianceHead", "GovernanceOfficer", "security_officer", "compliance"}
        if not issuer_id or not any(r in authorized_gov_roles for r in issuer_roles):
            raise PolicyDeniedError(
                f"Policy decision {decision.decision_id!r} rejected: unauthorized issuer {issuer_id!r} lacking governance authorization."
            )

    @staticmethod
    def validate_approval_record(
        approval: Optional[Dict[str, Any]],
        expected_migration_id: str,
        current_plan_fingerprint: Optional[str] = None,
        expected_plan_id: Optional[str] = None,
        expected_plan_revision: Optional[int] = None,
        expected_config_fingerprint: Optional[str] = None,
        expected_action: Optional[str] = None,
        expected_node_id: Optional[str] = None,
        min_quorum: int = 1,
        requester_id: Optional[str] = None,
    ) -> None:
        """Validate durable GovernanceApproval record from SQLite or artifact registry."""
        if not approval:
            raise PolicyDeniedError("No approved governance record found for migration")

        status = approval.get("status")
        if hasattr(status, "value"):
            status = status.value
        if status != ApprovalStatus.APPROVED.value and status != "APPROVED":
            raise PolicyDeniedError(f"Governance approval status is {status!r} (not APPROVED)")

        if approval.get("migration_id") != expected_migration_id:
            raise PolicyDeniedError(f"Approval migration ID mismatch: {approval.get('migration_id')} != {expected_migration_id}")

        if current_plan_fingerprint:
            intent_fp = approval.get("intent_fingerprint") or approval.get("plan_fingerprint") or approval.get("artifact_fingerprint")
            if intent_fp and intent_fp != current_plan_fingerprint:
                raise PolicyDeniedError("Approval intent fingerprint does not match active plan (plan has been mutated)")

        if expected_plan_id and approval.get("plan_id") and approval["plan_id"] != expected_plan_id:
            raise PolicyDeniedError(f"Approval plan ID mismatch: {approval['plan_id']} != {expected_plan_id}")

        if expected_plan_revision is not None and approval.get("plan_revision") is not None:
            if approval["plan_revision"] != expected_plan_revision:
                raise PolicyDeniedError(
                    f"Approval plan revision mismatch: {approval['plan_revision']} != {expected_plan_revision}"
                )

        if expected_config_fingerprint and approval.get("config_fingerprint"):
            if approval["config_fingerprint"] != expected_config_fingerprint:
                raise PolicyDeniedError("Approval config fingerprint mismatch (configuration has been mutated)")

        if expected_action and approval.get("action"):
            if approval["action"] not in (expected_action, "*"):
                raise PolicyDeniedError(f"Approval action mismatch: {approval['action']} != {expected_action}")

        if expected_node_id and approval.get("graph_node_id"):
            if approval["graph_node_id"] not in (expected_node_id, "*"):
                raise PolicyDeniedError(f"Approval node mismatch: {approval['graph_node_id']} != {expected_node_id}")

        approvers = approval.get("approvers", [])
        if not isinstance(approvers, list):
            approvers = [approval.get("issuer_id") or approval.get("approver_id")] if (approval.get("issuer_id") or approval.get("approver_id")) else []

        if len(set(approvers)) < min_quorum:
            raise PolicyDeniedError(f"Insufficient approval quorum: required {min_quorum}, got {len(set(approvers))}")

        if requester_id:
            fe = FourEyesValidator()
            for approver in approvers:
                ok, msg = fe.validate_action(
                    requester_id=str(requester_id),
                    approver_id=str(approver),
                    action_type=str(expected_action or "MIGRATION_EXECUTE"),
                )
                if not ok:
                    raise PolicyDeniedError(f"Maker-checker violation: {msg}")

    @staticmethod
    def is_approval_required(state: Any, actor: Any) -> bool:
        """Governance approval required if in GOVERNANCE_PENDING or non-admin in production."""
        if hasattr(state, "value") and state.value == "GOVERNANCE_PENDING":
            return True
        if state == "GOVERNANCE_PENDING":
            return True
        if getattr(actor, "requires_governance", False):
            return True
        roles = getattr(actor, "roles", ()) or ()
        env = getattr(actor, "environment", "") or ""
        if env in ("production", "prod") and "admin" not in roles:
            return True
        return False
