"""tests/unit/engine_intelligence/test_p7c_checklist_foundations.py
=======================================================================
P7C brief §14 items 16 (budget dimensions), 23 (outcome tracking), 24 (task-
specific evaluation foundation), 25 (shadow-evaluation architecture foundation).
Closes a Group-1 freeze reconciliation gap: these items require Group-1 to
establish real foundation/contracts, not defer them wholesale to Group 2.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.budget import (
    MonetaryBudget,
    RequestBudget,
    TokenBudget,
    check_budget_and_cancellation,
)
from akaalEngine.intelligence.evaluation import (
    ComparisonVerdict,
    EvaluationCriterion,
    EvaluationResult,
    OutcomeRecord,
    OutcomeStore,
    ShadowComparisonResult,
    compare_evaluation_sets,
)
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import (
    IntelligenceBudgetExceededError,
    IntelligenceTenantBoundaryError,
)
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
            project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
            model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
        );
        CREATE TABLE intelligence_outcomes (
            outcome_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
            outcome_status TEXT NOT NULL, observed_at TEXT NOT NULL, detail TEXT, metrics TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    yield connection
    connection.close()


def _req(**overrides) -> IntelligenceRequest:
    base = dict(
        task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id="plan-1", subject_version="v1", requested_by="user-1",
    )
    base.update(overrides)
    return IntelligenceRequest(**base)


def _ctx(**overrides) -> IntelligenceContext:
    base = dict(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
    base.update(overrides)
    return IntelligenceContext(**base)


class TestTokenAndMonetaryBudgets:
    def test_token_budget_exceeded_raises(self):
        budget = TokenBudget(max_tokens=100, consumed_tokens=100)
        with pytest.raises(IntelligenceBudgetExceededError):
            check_budget_and_cancellation(None, None, token_budget=budget)

    def test_token_budget_within_limit_does_not_raise(self):
        budget = TokenBudget(max_tokens=100, consumed_tokens=50)
        check_budget_and_cancellation(None, None, token_budget=budget)  # must not raise

    def test_token_budget_record_usage_is_immutable_and_cumulative(self):
        budget = TokenBudget(max_tokens=100)
        updated = budget.record_usage(30)
        assert budget.consumed_tokens == 0  # original untouched
        assert updated.consumed_tokens == 30
        assert updated.remaining() == 70

    def test_hostile_negative_token_usage_rejected(self):
        budget = TokenBudget(max_tokens=100)
        with pytest.raises(ValueError):
            budget.record_usage(-5)

    def test_monetary_budget_exceeded_raises(self):
        budget = MonetaryBudget(max_amount=10.0, consumed_amount=10.0)
        with pytest.raises(IntelligenceBudgetExceededError):
            check_budget_and_cancellation(None, None, monetary_budget=budget)

    def test_monetary_budget_record_spend(self):
        budget = MonetaryBudget(max_amount=10.0)
        updated = budget.record_spend(4.5)
        assert updated.remaining() == pytest.approx(5.5)

    def test_hostile_zero_max_amount_rejected_at_construction(self):
        with pytest.raises(ValueError):
            MonetaryBudget(max_amount=0)

    def test_token_budget_exactly_at_boundary_is_exceeded(self):
        """is_exceeded uses >=, not > -- exactly-at-limit must count as exceeded,
        never silently allowed one request past the limit."""
        budget = TokenBudget(max_tokens=100).record_usage(100)
        assert budget.is_exceeded() is True
        with pytest.raises(IntelligenceBudgetExceededError):
            check_budget_and_cancellation(None, None, token_budget=budget)

    def test_token_budget_one_below_boundary_not_exceeded(self):
        budget = TokenBudget(max_tokens=100).record_usage(99)
        assert budget.is_exceeded() is False

    def test_monetary_budget_exactly_at_boundary_is_exceeded(self):
        budget = MonetaryBudget(max_amount=10.0).record_spend(10.0)
        assert budget.is_exceeded() is True

    def test_hostile_negative_max_tokens_rejected(self):
        with pytest.raises(ValueError):
            TokenBudget(max_tokens=-1)

    def test_hostile_negative_max_amount_rejected(self):
        with pytest.raises(ValueError):
            MonetaryBudget(max_amount=-5.0)

    def test_cancellation_checked_even_when_budgets_are_fine(self):
        """Cancellation and budget checks are independent gates -- a cancelled
        request must be rejected even if every budget dimension still has
        headroom (no silent 'budget OK so ignore cancellation' fallback)."""
        from akaalEngine.intelligence.budget import CancellationToken
        from akaalEngine.intelligence.models.errors import IntelligenceCancelledError

        token = CancellationToken()
        token.cancel()
        healthy_time = RequestBudget(max_seconds=999.0)
        healthy_tokens = TokenBudget(max_tokens=999999)
        healthy_money = MonetaryBudget(max_amount=999999.0)
        with pytest.raises(IntelligenceCancelledError):
            check_budget_and_cancellation(healthy_time, token, token_budget=healthy_tokens, monetary_budget=healthy_money)

    def test_exceeded_token_budget_checked_even_when_time_budget_is_fine(self):
        """Multiple budget dimensions are independent gates -- exceeding ANY one
        must reject, even when every other dimension is healthy (no silent
        'time budget OK so proceed regardless of tokens' fallback)."""
        healthy_time = RequestBudget(max_seconds=999.0)
        exhausted_tokens = TokenBudget(max_tokens=10).record_usage(10)
        with pytest.raises(IntelligenceBudgetExceededError):
            check_budget_and_cancellation(healthy_time, None, token_budget=exhausted_tokens)


class TestOutcomeTracking:
    def test_record_and_list_outcome_via_kernel(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        outcome = kernel.record_outcome(
            artifact_id=artifact.artifact_id, tenant_id="tenant-a", outcome_status="SUCCEEDED",
            conn=conn, detail="wave plan executed cleanly", metrics={"duration_seconds": 42},
        )
        assert outcome.outcome_status == "SUCCEEDED"
        listed = kernel.list_outcomes(artifact.artifact_id, conn)
        assert len(listed) == 1
        assert listed[0].metrics["duration_seconds"] == 42

    def test_multiple_outcomes_accumulate_in_order(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        kernel.record_outcome(artifact_id=artifact.artifact_id, tenant_id="tenant-a", outcome_status="PARTIALLY_SUCCEEDED", conn=conn)
        kernel.record_outcome(artifact_id=artifact.artifact_id, tenant_id="tenant-a", outcome_status="SUCCEEDED", conn=conn)
        listed = kernel.list_outcomes(artifact.artifact_id, conn)
        assert len(listed) == 2
        assert [o.outcome_status for o in listed] == ["PARTIALLY_SUCCEEDED", "SUCCEEDED"]

    def test_hostile_cross_tenant_outcome_recording_rejected(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        artifact = kernel.submit_request(_req(tenant_id="tenant-a"), _ctx(tenant_id="tenant-a"), conn)
        with pytest.raises(IntelligenceTenantBoundaryError):
            kernel.record_outcome(artifact_id=artifact.artifact_id, tenant_id="tenant-b", outcome_status="SUCCEEDED", conn=conn)

    def test_invalid_outcome_status_rejected(self):
        with pytest.raises(ValueError):
            OutcomeRecord.new(artifact_id="a1", tenant_id="tenant-a", outcome_status="MAYBE_FINE_WHO_KNOWS")


class TestEvaluationFoundation:
    def test_criterion_and_result_are_typed_and_bounded(self):
        criterion = EvaluationCriterion(name="compatibility_completeness", description="test", weight=0.5)
        result = EvaluationResult.new(artifact_id="a1", criterion_name=criterion.name, score=0.8, evaluated_by="reviewer-1")
        assert 0.0 <= result.score <= 1.0

    def test_hostile_out_of_range_score_rejected(self):
        with pytest.raises(ValueError):
            EvaluationResult.new(artifact_id="a1", criterion_name="x", score=1.5, evaluated_by="reviewer-1")

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            EvaluationCriterion(name="x", description="d", weight=-1.0)


class TestEvaluationComparisonNonFake:
    """compare_evaluation_sets must be a real function of its inputs -- not a
    hardcoded outcome. Each test supplies different real scores and checks the
    genuinely different, correct verdict."""

    def _result(self, score, criterion="quality", is_hard_gate=False):
        return EvaluationResult.new(artifact_id="a1", criterion_name=criterion, score=score, evaluated_by="reviewer-1", is_hard_gate=is_hard_gate)

    def test_candidate_better(self):
        verdict = compare_evaluation_sets(candidate_results=[self._result(0.9)], current_results=[self._result(0.5)])
        assert verdict == ComparisonVerdict.CANDIDATE_BETTER

    def test_current_better(self):
        verdict = compare_evaluation_sets(candidate_results=[self._result(0.3)], current_results=[self._result(0.8)])
        assert verdict == ComparisonVerdict.CURRENT_BETTER

    def test_equal(self):
        verdict = compare_evaluation_sets(candidate_results=[self._result(0.7)], current_results=[self._result(0.7)])
        assert verdict == ComparisonVerdict.EQUAL

    def test_weighted_criteria_change_the_outcome(self):
        """Same raw scores, different weights -> genuinely different verdict --
        proves weights are actually used, not decorative."""
        criteria = [EvaluationCriterion(name="speed", description="d", weight=0.1), EvaluationCriterion(name="safety", description="d", weight=10.0)]
        candidate = [self._result(1.0, criterion="speed"), self._result(0.4, criterion="safety")]
        current = [self._result(0.4, criterion="speed"), self._result(1.0, criterion="safety")]
        verdict = compare_evaluation_sets(candidate_results=candidate, current_results=current, criteria=criteria)
        assert verdict == ComparisonVerdict.CURRENT_BETTER  # safety dominates due to weight

    def test_hostile_hard_gate_failure_cannot_be_averaged_away(self):
        """Candidate scores near-perfect on every other criterion but fails one
        hard-gate criterion -- must still be rejected, never win on average."""
        candidate = [self._result(1.0, criterion="speed"), self._result(1.0, criterion="cost"), self._result(0.0, criterion="tenant_isolation", is_hard_gate=True)]
        current = [self._result(0.5, criterion="speed"), self._result(0.5, criterion="cost"), self._result(1.0, criterion="tenant_isolation", is_hard_gate=True)]
        verdict = compare_evaluation_sets(candidate_results=candidate, current_results=current)
        assert verdict == ComparisonVerdict.CANDIDATE_REJECTED_HARD_GATE_FAILURE

    def test_current_hard_gate_failure_also_detected(self):
        candidate = [self._result(1.0, criterion="tenant_isolation", is_hard_gate=True)]
        current = [self._result(0.0, criterion="tenant_isolation", is_hard_gate=True)]
        verdict = compare_evaluation_sets(candidate_results=candidate, current_results=current)
        assert verdict == ComparisonVerdict.CURRENT_REJECTED_HARD_GATE_FAILURE

    def test_both_hard_gate_failure(self):
        candidate = [self._result(0.0, criterion="tenant_isolation", is_hard_gate=True)]
        current = [self._result(0.0, criterion="tenant_isolation", is_hard_gate=True)]
        verdict = compare_evaluation_sets(candidate_results=candidate, current_results=current)
        assert verdict == ComparisonVerdict.BOTH_REJECTED_HARD_GATE_FAILURE

    def test_hard_gate_property_is_binary_not_gradient(self):
        near_perfect_but_not_exact = EvaluationResult.new(artifact_id="a1", criterion_name="x", score=0.999, evaluated_by="r", is_hard_gate=True)
        assert near_perfect_but_not_exact.hard_gate_passed is False

    def test_non_hard_gate_result_always_reports_passed(self):
        low_score_soft = EvaluationResult.new(artifact_id="a1", criterion_name="x", score=0.1, evaluated_by="r", is_hard_gate=False)
        assert low_score_soft.hard_gate_passed is True


class TestShadowEvaluationFoundation:
    def test_identical_results_agree(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        prod = kernel.submit_request(_req(), _ctx(), conn)
        shadow = kernel.submit_request(_req(subject_id="plan-2"), _ctx(subject_id="plan-2"), conn)
        # Same producer, same deterministic logic run on different (but
        # equivalent) subjects still gives distinct fingerprints -- compare
        # against itself to prove the "agree" path is real, not hardcoded True.
        comparison = ShadowComparisonResult.compare(production_artifact=prod, shadow_artifact=prod, tenant_id="tenant-a")
        assert comparison.agree is True

    def test_divergent_results_disagree(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        prod = kernel.submit_request(_req(subject_id="plan-1"), _ctx(subject_id="plan-1"), conn)
        shadow = kernel.submit_request(_req(subject_id="plan-2"), _ctx(subject_id="plan-2"), conn)
        comparison = ShadowComparisonResult.compare(production_artifact=prod, shadow_artifact=shadow, tenant_id="tenant-a")
        assert comparison.agree is False
        assert comparison.divergence_summary != ""
