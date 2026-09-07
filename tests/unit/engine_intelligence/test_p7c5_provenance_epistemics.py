"""tests/unit/engine_intelligence/test_p7c5_provenance_epistemics.py
=======================================================================
P7C.5 Provenance, Epistemics, Explainability & Staleness: epistemic typing is
structural (not just UI text), evidence-grounded confidence, counterfactual
explanations, and automatic supersession on regeneration.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    CounterfactualExplanation,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
            project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
            model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
        )
        """
    )
    yield connection
    connection.close()


class TestEpistemicTypingIsStructural:
    def test_fact_and_prediction_are_distinct_enum_values(self):
        assert EpistemicType.FACT != EpistemicType.PREDICTION
        assert EpistemicType.RECOMMENDATION != EpistemicType.ASSUMPTION

    def test_result_carries_its_epistemic_type_in_serialized_form(self):
        result = IntelligenceResult(
            task=IntelligenceTask.FORECAST,
            epistemic_type=EpistemicType.PREDICTION,
            summary="test",
            explanation=Explanation(summary="test"),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=0.5),
        )
        assert result.to_dict()["epistemic_type"] == "PREDICTION"


class TestConfidenceEvidence:
    def test_rejects_out_of_range_coverage(self):
        with pytest.raises(ValueError):
            ConfidenceEvidence(evidence_coverage=1.5)
        with pytest.raises(ValueError):
            ConfidenceEvidence(evidence_coverage=-0.1)

    def test_missing_information_and_contradictions_are_first_class(self):
        ce = ConfidenceEvidence(
            evidence_coverage=0.4,
            missing_information=["no telemetry for last 24h"],
            contradictory_evidence=["source A says X, source B says not X"],
        )
        d = ce.to_dict()
        assert d["missing_information"] == ["no telemetry for last 24h"]
        assert d["contradictory_evidence"] == ["source A says X, source B says not X"]


class TestCounterfactualExplanation:
    def test_counterfactual_names_concrete_blocking_constraint(self):
        cf = CounterfactualExplanation(
            rejected_alternative="route via singapore region",
            blocking_constraint="residency_policy:india-only",
            would_require_change="residency policy would need to permit non-India regions",
        )
        d = cf.to_dict()
        assert d["blocking_constraint"] == "residency_policy:india-only"

    def test_explanation_serializes_embedded_counterfactuals(self):
        explanation = Explanation(
            summary="Singapore excluded",
            counterfactuals=[
                CounterfactualExplanation(
                    rejected_alternative="singapore",
                    blocking_constraint="residency_policy:india-only",
                    would_require_change="policy change required",
                )
            ],
        )
        d = explanation.to_dict()
        assert len(d["counterfactuals"]) == 1
        assert d["counterfactuals"][0]["rejected_alternative"] == "singapore"


class TestAutomaticSupersession:
    def _req(self, **overrides):
        base = dict(
            task=IntelligenceTask.QUERY,
            tenant_id="tenant-a",
            subject_type="migration_plan",
            subject_id="plan-1",
            subject_version="v1",
            requested_by="user-1",
        )
        base.update(overrides)
        return IntelligenceRequest(**base)

    def _ctx(self, **overrides):
        base = dict(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        base.update(overrides)
        return IntelligenceContext(**base)

    def test_regenerating_supersedes_prior_artifact(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        first = kernel.submit_request(self._req(), self._ctx(), conn, supersede_previous=True)
        second = kernel.submit_request(self._req(), self._ctx(subject_version="v2"), conn, supersede_previous=True)

        refetched_first = kernel.get_artifact(first.artifact_id, conn)
        assert refetched_first.lifecycle_state == ArtifactLifecycleState.SUPERSEDED
        assert refetched_first.superseded_by == second.artifact_id

    def test_supersession_never_touches_different_task_or_subject(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        other_subject = kernel.submit_request(
            self._req(subject_id="plan-2"), self._ctx(subject_id="plan-2"), conn, supersede_previous=True
        )
        kernel.submit_request(self._req(), self._ctx(), conn, supersede_previous=True)

        refetched = kernel.get_artifact(other_subject.artifact_id, conn)
        assert refetched.lifecycle_state == ArtifactLifecycleState.GENERATED

    def test_without_supersede_flag_prior_artifact_untouched(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        first = kernel.submit_request(self._req(), self._ctx(), conn)
        kernel.submit_request(self._req(), self._ctx(subject_version="v2"), conn)

        refetched_first = kernel.get_artifact(first.artifact_id, conn)
        assert refetched_first.lifecycle_state == ArtifactLifecycleState.GENERATED

    def test_hostile_already_terminal_artifact_not_reopened_by_supersession(self, conn):
        """A REJECTED artifact must never be silently flipped to SUPERSEDED by a
        later regeneration -- terminal states are permanent."""
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        first = kernel.submit_request(self._req(), self._ctx(), conn)
        kernel.transition(first.artifact_id, ArtifactLifecycleState.REJECTED, conn)

        kernel.submit_request(self._req(), self._ctx(subject_version="v2"), conn, supersede_previous=True)

        refetched = kernel.get_artifact(first.artifact_id, conn)
        assert refetched.lifecycle_state == ArtifactLifecycleState.REJECTED
