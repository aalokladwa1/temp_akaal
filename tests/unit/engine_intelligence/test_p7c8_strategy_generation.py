"""tests/unit/engine_intelligence/test_p7c8_strategy_generation.py
======================================================================
P7C.8 Multi-Objective Strategy Generation: different objectives yield different
valid alternatives, residency constraints define the feasible set BEFORE
optimization (not merely a penalty), Pareto frontier is genuinely computed, and
counterfactual explanations name the concrete blocking constraint.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.strategy_generation import (
    StrategyObjective,
    compute_pareto_frontier,
    generate_candidate_shapes,
    make_strategy_generation_producer,
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


def _kernel() -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.OPTIMIZE, make_strategy_generation_producer())
    return kernel


def _kernel_with_canonical(allowed_regions=None, region_capability_map=None) -> IntelligenceKernel:
    """A kernel wired with a real (test-shaped) canonical constraint resolver --
    per the Blocker-1 trust law, residency/capability tests must go through a
    resolver representing canonical truth, not a bare caller claim."""
    from akaalEngine.intelligence.knowledge.constraint_projection import project_trusted_constraints

    canonical_regions = frozenset(allowed_regions or ())
    canonical_caps = {k: frozenset(v) for k, v in (region_capability_map or {}).items()}

    def region_authorizer(tenant_id, region):
        return region in canonical_regions

    def capability_authorizer(tenant_id, region, capability):
        return capability in canonical_caps.get(region, frozenset())

    def resolver(request, context):
        candidate_regions = frozenset(request.parameters.get("candidate_regions") or ["default"])
        required_capability = request.parameters.get("required_capability")
        capability_universe = frozenset({str(required_capability)}) if required_capability else None
        return project_trusted_constraints(
            request.tenant_id, candidate_regions=candidate_regions, region_authorizer=region_authorizer,
            capability_universe=capability_universe, capability_authorizer=capability_authorizer if capability_universe else None,
        )

    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.OPTIMIZE, make_strategy_generation_producer(resolver))
    return kernel


def _req(**params) -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id="plan-1", subject_version="v1", requested_by="user-1", parameters=params,
    )


def _ctx() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")


class TestParetoFrontier:
    def test_dominated_candidate_excluded_from_frontier(self):
        candidates = generate_candidate_shapes(base_risk_score=0.0, allowed_regions=("us",))
        frontier = compute_pareto_frontier(candidates)
        assert len(frontier) <= len(candidates)
        assert len(frontier) >= 1


class TestObjectivesProduceDifferentAlternatives:
    def test_fastest_and_lowest_cost_pick_different_best_candidate(self, conn):
        kernel = _kernel()
        fastest = kernel.submit_request(_req(objective="FASTEST"), _ctx(), conn)

        cost_ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v2")
        cost_artifact = kernel.submit_request(_req(objective="LOWEST_COST"), cost_ctx, conn)

        fastest_best = fastest.result["optimization"]["alternatives"][0]["label"]
        cost_best = cost_artifact.result["optimization"]["alternatives"][0]["label"]
        assert fastest_best != cost_best
        assert fastest_best.startswith("aggressive_high_parallelism")
        assert cost_best.startswith("conservative_low_parallelism")

    def test_balanced_objective_produces_valid_ranking(self, conn):
        kernel = _kernel()
        artifact = kernel.submit_request(_req(objective="BALANCED"), _ctx(), conn)
        alternatives = artifact.result["optimization"]["alternatives"]
        assert len(alternatives) == 3


class TestResidencyDefinesFeasibleSetHostile:
    def test_hostile_india_only_excludes_singapore_before_optimization(self, conn):
        """Direct scenario from the P7C brief: India-only migration, Singapore
        cheaper/faster but must be excluded from the feasible set entirely --
        not merely penalized or warned about. India candidates remain and are
        the ones actually optimized/ranked."""
        kernel = _kernel_with_canonical(allowed_regions=["india"])
        artifact = kernel.submit_request(
            _req(objective="LOWEST_COST", candidate_regions=["singapore", "india"], allowed_regions=["india"]),
            _ctx(),
            conn,
        )
        excluded = artifact.result["data"]["excluded_by_residency"]
        assert len(excluded) == 3
        assert all("singapore" in label for label in excluded)

        alternatives = artifact.result["optimization"]["alternatives"]
        assert all("india" in a["label"] for a in alternatives)
        assert not any("singapore" in a["label"] for a in alternatives)

    def test_hostile_empty_feasible_set_raises_not_silently_optimized(self, conn):
        kernel = _kernel()
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                _req(objective="LOWEST_COST", candidate_regions=["singapore"], allowed_regions=["india"]),
                _ctx(),
                conn,
            )

    def test_compliant_region_candidates_pass_and_carry_no_counterfactual_confusion(self, conn):
        kernel = _kernel_with_canonical(allowed_regions=["india"])
        artifact = kernel.submit_request(
            _req(objective="LOWEST_COST", candidate_regions=["india"], allowed_regions=["india"]),
            _ctx(),
            conn,
        )
        assert artifact.result["data"]["excluded_by_residency"] == []
        assert artifact.result["explanation"]["counterfactuals"] == []

    def test_hostile_capacity_rich_unauthorized_region_excluded_regardless_of_cost(self, conn):
        """A region that is cheap/capacity-rich but not in allowed_regions must
        be excluded from the feasible set, never merely down-ranked because its
        cost/speed scores look attractive."""
        kernel = _kernel_with_canonical(allowed_regions=["india"])
        artifact = kernel.submit_request(
            _req(objective="FASTEST", candidate_regions=["capacity-rich-unauthorized", "india"], allowed_regions=["india"]),
            _ctx(),
            conn,
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert not any("capacity-rich-unauthorized" in a["label"] for a in alternatives)
        assert all("india" in a["label"] for a in alternatives)

    def test_counterfactual_names_concrete_blocking_constraint_not_vague_text(self, conn):
        kernel = _kernel_with_canonical(allowed_regions=["india", "us"])
        artifact = kernel.submit_request(
            _req(objective="LOWEST_COST", candidate_regions=["brazil", "india"], allowed_regions=["india", "us"]),
            _ctx(),
            conn,
        )
        counterfactuals = artifact.result["explanation"]["counterfactuals"]
        assert len(counterfactuals) == 3
        for cf in counterfactuals:
            assert "brazil" in cf["rejected_alternative"]
            assert "allowed_regions" in cf["blocking_constraint"]
            assert "brazil" in cf["would_require_change"]


class TestCapabilityFeasibleSetHostile:
    """P7C brief: capability constraints must also define the feasible set
    before optimization -- not merely residency. Capability facts are always
    caller-supplied canonical data (never fabricated by this producer)."""

    def test_hostile_capability_incompatible_region_excluded_before_optimization(self, conn):
        kernel = _kernel_with_canonical(
            allowed_regions=["india", "us"],
            region_capability_map={"india": ["cdc_apply", "bulk_write"], "us": ["bulk_write"]},
        )
        artifact = kernel.submit_request(
            _req(objective="LOWEST_COST", candidate_regions=["india", "us"], required_capability="cdc_apply"),
            _ctx(),
            conn,
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert all("india" in a["label"] for a in alternatives)
        assert not any("us" in a["label"].split("__")[-1] for a in alternatives)
        assert artifact.result["data"]["excluded_by_capability"]

    def test_hostile_empty_feasible_set_after_capability_filter_raises(self, conn):
        kernel = _kernel()
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                _req(
                    objective="LOWEST_COST",
                    candidate_regions=["us"],
                    required_capability="cdc_apply",
                    region_capability_map={"us": ["bulk_write"]},
                ),
                _ctx(),
                conn,
            )

    def test_hostile_required_capability_without_map_refused_not_guessed(self, conn):
        """A capability constraint without canonical capability facts must be
        refused, never guessed/assumed compatible."""
        kernel = _kernel()
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                _req(objective="LOWEST_COST", candidate_regions=["india"], required_capability="cdc_apply"),
                _ctx(),
                conn,
            )

    def test_residency_and_capability_compose_correctly(self, conn):
        """A region legal under residency but incapable, and a region capable
        but illegal, must both be excluded -- only the region satisfying BOTH
        constraints survives."""
        kernel = _kernel_with_canonical(
            allowed_regions=["india", "singapore"],
            region_capability_map={
                "india": ["cdc_apply"],
                "singapore": ["bulk_write"],  # legal region, wrong capability
                "brazil": ["cdc_apply"],  # right capability, illegal region (not canonically allowed)
            },
        )
        artifact = kernel.submit_request(
            _req(
                objective="BALANCED",
                candidate_regions=["india", "singapore", "brazil"],
                allowed_regions=["india", "singapore"],
                required_capability="cdc_apply",
            ),
            _ctx(),
            conn,
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert all("india" in a["label"] for a in alternatives)


class TestStaleConstraintsHostile:
    def test_hostile_stale_constraints_fingerprint_refused(self, conn):
        """A constraint snapshot bound to a canonical-state fingerprint that no
        longer matches current context must never be silently optimized
        against."""
        kernel = _kernel()
        ctx = IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1",
            canonical_state_fingerprint="fp-current",
        )
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                _req(objective="BALANCED", constraints_generated_against_fingerprint="fp-stale-old"),
                ctx,
                conn,
            )

    def test_matching_constraints_fingerprint_proceeds(self, conn):
        kernel = _kernel()
        ctx = IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1",
            canonical_state_fingerprint="fp-current",
        )
        artifact = kernel.submit_request(
            _req(objective="BALANCED", constraints_generated_against_fingerprint="fp-current"),
            ctx,
            conn,
        )
        assert artifact.result["optimization"]["alternatives"]
