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
        target_artifact_fingerprint: Optional[str] = None,
        current_time_iso: Optional[str] = None,
    ) -> None:
        """Evaluates policy decision against fingerprint and expiration. Raises PolicyDeniedError on failure."""
        if decision is None:
            raise PolicyDeniedError("No policy decision provided (POLICY_DENIED).")

        if decision.result == PolicyResult.DENY:
            raise PolicyDeniedError(f"Policy denied execution: {decision.reason}")

        if decision.result == PolicyResult.REQUIRE_APPROVAL:
            raise PolicyDeniedError(f"Action requires explicit governance approval: {decision.reason}")

        if decision.is_expired(current_time_iso):
            raise PolicyDeniedError(f"Policy decision {decision.decision_id!r} has expired (EXPIRED).")

        if target_artifact_fingerprint and decision.resource.artifact_fingerprint:
            if decision.resource.artifact_fingerprint != target_artifact_fingerprint:
                raise PolicyDeniedError(
                    f"Policy decision artifact fingerprint mismatch: expected {target_artifact_fingerprint!r}, got {decision.resource.artifact_fingerprint!r} (material change invalidates approval)."
                )
