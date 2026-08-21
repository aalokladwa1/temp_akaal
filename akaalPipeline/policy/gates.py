"""akaalPipeline.policy.gates
============================
Policy gate evaluator validating policy decisions and artifact fingerprints.
"""

from __future__ import annotations

from typing import Optional
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

        # 1. Resource binding check (binds approval to exact migration/resource)
        if expected_resource_id:
            decision_res_id = getattr(getattr(decision, "resource", None), "resource_id", None)
            if decision_res_id != expected_resource_id:
                raise PolicyDeniedError(
                    f"Policy decision resource ID mismatch: expected {expected_resource_id!r}, got {decision_res_id!r}."
                )

        # 2. Action binding check (binds approval to authorized start action)
        if expected_action:
            decision_action = getattr(getattr(decision, "action", None), "name", "")
            if decision_action not in (expected_action, "migration.start", "start_migration", "*"):
                raise PolicyDeniedError(
                    f"Policy decision action mismatch: expected {expected_action!r}, got {decision_action!r}."
                )

        # 3. Subject binding check (if subject is specified and not wildcard, must match requesting actor)
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

        # 5. Validate that approval was issued by an authorized governance authority
        issuer_roles = getattr(decision, "issuer_roles", []) or []
        issuer_id = getattr(decision, "issuer_id", None)
        if not issuer_id or not any(r in ("admin", "governor", "security_officer", "compliance") for r in issuer_roles):
            raise PolicyDeniedError(
                f"Policy decision {decision.decision_id!r} rejected: unauthorized issuer {issuer_id!r} lacking governance authorization."
            )


    @staticmethod
    def is_approval_required(state: Any, actor: Any) -> bool:
        """Pipeline-determined rule: governance is mandatory if in GOVERNANCE_PENDING or production environment without admin."""
        if hasattr(state, "value") and state.value == "GOVERNANCE_PENDING":
            return True
        if getattr(actor, "environment", "") in ("production", "prod") and "admin" not in getattr(actor, "roles", ()):
            return True
        return False
