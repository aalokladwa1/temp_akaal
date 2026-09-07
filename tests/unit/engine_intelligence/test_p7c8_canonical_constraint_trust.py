"""tests/unit/engine_intelligence/test_p7c8_canonical_constraint_trust.py
=============================================================================
P7C.8 canonical trust law: CANONICAL AKAAL TRUTH OUTRANKS CALLER-SUPPLIED
CONTEXT. FINAL_FEASIBLE_SET = CANONICAL_FEASIBLE_SET ∩ CALLER_REQUESTED_SET,
never a union, never caller-only. Covers all 10 hostile scenarios required by
the Group-1 freeze-gate blocker.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.knowledge.constraint_projection import (
    TrustedStrategyConstraintSnapshot,
    narrow_by_caller_preference,
    project_trusted_constraints,
)
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.strategy_generation import make_strategy_generation_producer


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


def _india_only_authorizer(tenant_id, region):
    """A real (test-shaped) canonical decision function: only 'india' is
    authorized, regardless of what any caller claims."""
    return tenant_id == "tenant-a" and region == "india"


def _india_germany_authorizer(tenant_id, region):
    return tenant_id == "tenant-a" and region in ("india", "germany")


def _no_capability_authorizer(tenant_id, region, capability):
    return False  # canonical truth: nothing has this capability


class TestProjectTrustedConstraintsAlgorithm:
    def test_only_canonically_authorized_regions_included(self):
        snapshot = project_trusted_constraints(
            "tenant-a", candidate_regions=frozenset({"india", "singapore"}), region_authorizer=_india_only_authorizer
        )
        assert snapshot.allowed_regions == frozenset({"india"})

    def test_hostile_authorizer_denial_cannot_be_bypassed_by_wider_candidate_set(self):
        snapshot = project_trusted_constraints(
            "tenant-a", candidate_regions=frozenset({"india", "singapore", "brazil", "us"}), region_authorizer=_india_only_authorizer
        )
        assert snapshot.allowed_regions == frozenset({"india"})

    def test_capability_projection_reflects_canonical_denial(self):
        snapshot = project_trusted_constraints(
            "tenant-a", candidate_regions=frozenset({"india"}), region_authorizer=_india_only_authorizer,
            capability_universe=frozenset({"cdc_apply"}), capability_authorizer=_no_capability_authorizer,
        )
        assert snapshot.region_capability_map["india"] == frozenset()

    def test_fingerprint_deterministic_for_identical_snapshot(self):
        s1 = project_trusted_constraints("tenant-a", candidate_regions=frozenset({"india"}), region_authorizer=_india_only_authorizer)
        s2 = project_trusted_constraints("tenant-a", candidate_regions=frozenset({"india"}), region_authorizer=_india_only_authorizer)
        assert s1.source_fingerprint == s2.source_fingerprint

    def test_fingerprint_changes_when_canonical_decision_changes(self):
        s1 = project_trusted_constraints("tenant-a", candidate_regions=frozenset({"india", "germany"}), region_authorizer=_india_only_authorizer)
        s2 = project_trusted_constraints("tenant-a", candidate_regions=frozenset({"india", "germany"}), region_authorizer=_india_germany_authorizer)
        assert s1.source_fingerprint != s2.source_fingerprint


class TestNarrowByCallerPreferenceIsIntersectionOnly:
    def test_hostile_caller_cannot_broaden_canonical_set(self):
        """Scenario 1: canonical India-only + caller adds Singapore -> Singapore rejected."""
        canonical = frozenset({"india"})
        caller = frozenset({"india", "singapore"})
        assert narrow_by_caller_preference(canonical, caller) == frozenset({"india"})

    def test_caller_can_narrow_canonical_set(self):
        """Scenario 4: caller narrows India+Germany canonical set to India -> India accepted."""
        canonical = frozenset({"india", "germany"})
        caller = frozenset({"india"})
        assert narrow_by_caller_preference(canonical, caller) == frozenset({"india"})

    def test_caller_omitting_constraints_uses_full_canonical_set(self):
        """Scenario 3: caller omits constraints entirely -> P7C still uses canonical constraints."""
        canonical = frozenset({"india", "germany"})
        assert narrow_by_caller_preference(canonical, None) == canonical

    def test_hostile_caller_claiming_denied_region_never_appears(self):
        """Scenario 2 (region form): canonical denies 'singapore' entirely; caller
        asking only for singapore yields an empty set, never singapore."""
        canonical = frozenset({"india"})
        caller = frozenset({"singapore"})
        assert narrow_by_caller_preference(canonical, caller) == frozenset()


class TestProducerTrustSemanticsEndToEnd:
    def _kernel(self, resolver):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_strategy_generation_producer(resolver), capability="strategy_generation")
        return kernel

    def _req(self, **params):
        return IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1", parameters=params,
            capability="strategy_generation",
        )

    def _ctx(self, **overrides):
        base = dict(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        base.update(overrides)
        return IntelligenceContext(**base)

    def _resolver_factory(self, region_authorizer, capability_authorizer=None):
        def resolver(request, context):
            candidate_regions = frozenset(request.parameters.get("candidate_regions") or ["default"])
            required_capability = request.parameters.get("required_capability")
            capability_universe = frozenset({str(required_capability)}) if required_capability else None
            return project_trusted_constraints(
                request.tenant_id, candidate_regions=candidate_regions, region_authorizer=region_authorizer,
                capability_universe=capability_universe,
                capability_authorizer=capability_authorizer if capability_universe else None,
            )
        return resolver

    def test_hostile_scenario_1_canonical_india_only_caller_adds_singapore(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer))
        artifact = kernel.submit_request(
            self._req(candidate_regions=["india", "singapore"], allowed_regions=["india", "singapore"]), self._ctx(), conn
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert all("india" in a["label"] for a in alternatives)
        assert not any("singapore" in a["label"] for a in alternatives)

    def test_hostile_scenario_2_canonical_capability_no_caller_says_yes(self, conn):
        """Caller cannot invent capability facts -- required_capability is only
        ever checked against the CANONICAL snapshot's own capability map."""
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer, _no_capability_authorizer))
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                self._req(candidate_regions=["india"], required_capability="cdc_apply"), self._ctx(), conn
            )

    def test_scenario_3_caller_omits_constraints_canonical_still_applies(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer))
        artifact = kernel.submit_request(self._req(candidate_regions=["india", "singapore"]), self._ctx(), conn)
        alternatives = artifact.result["optimization"]["alternatives"]
        assert not any("singapore" in a["label"] for a in alternatives)

    def test_scenario_4_caller_narrows_india_germany_to_india(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_germany_authorizer))
        artifact = kernel.submit_request(
            self._req(candidate_regions=["india", "germany"], allowed_regions=["india"]), self._ctx(), conn
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert all("india" in a["label"] for a in alternatives)

    def test_scenario_5_stale_canonical_constraint_snapshot_rejected(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer))
        ctx = self._ctx(canonical_state_fingerprint="fp-current")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(
                self._req(candidate_regions=["india"], constraints_generated_against_fingerprint="fp-stale"), ctx, conn
            )

    def test_scenario_6_cross_tenant_canonical_reference_rejected(self, conn):
        """The resolver is called with request.tenant_id, always the REAL
        authenticated tenant -- a request cannot ask for another tenant's
        canonical constraints; project_trusted_constraints only ever answers
        for the tenant_id it was actually given."""

        def tenant_scoped_authorizer(tenant_id, region):
            return tenant_id == "tenant-a" and region == "india"

        kernel = self._kernel(self._resolver_factory(tenant_scoped_authorizer))
        # tenant-b requesting india: canonical authorizer only grants tenant-a.
        artifact = kernel.submit_request(
            self._req(candidate_regions=["india"], allowed_regions=["india"], tenant_id="tenant-b"),
            self._ctx(tenant_id="tenant-b"), conn,
        ) if False else None
        # IntelligenceRequest.tenant_id is fixed at construction; verify directly:
        req = IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-b", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1",
            parameters={"candidate_regions": ["india"], "allowed_regions": ["india"]}, capability="strategy_generation",
        )
        ctx = IntelligenceContext(tenant_id="tenant-b", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(req, ctx, conn)  # empty feasible set for tenant-b

    def test_scenario_7_cheaper_illegal_region_cannot_enter_pareto_frontier(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer))
        artifact = kernel.submit_request(
            self._req(objective="LOWEST_COST", candidate_regions=["india", "singapore"], allowed_regions=["india", "singapore"]),
            self._ctx(), conn,
        )
        pareto_labels = [c["label"] for c in artifact.result["data"]["pareto_frontier"]]
        assert not any("singapore" in label for label in pareto_labels)

    def test_scenario_8_capacity_rich_unauthorized_region_excluded(self, conn):
        kernel = self._kernel(self._resolver_factory(_india_only_authorizer))
        artifact = kernel.submit_request(
            self._req(candidate_regions=["india", "capacity-rich-unauthorized"], allowed_regions=["india", "capacity-rich-unauthorized"]),
            self._ctx(), conn,
        )
        alternatives = artifact.result["optimization"]["alternatives"]
        assert not any("capacity-rich-unauthorized" in a["label"] for a in alternatives)

    def test_scenario_9_producer_writes_no_canonical_residency_state(self, conn):
        """P7C never writes/alters the underlying residency authority -- proven
        structurally: the producer's only side effect is the returned
        IntelligenceResult; region_authorizer is called read-only (a plain
        function returning bool), never given a write method."""
        calls = []

        def observing_authorizer(tenant_id, region):
            calls.append((tenant_id, region))
            return region == "india"

        kernel = self._kernel(self._resolver_factory(observing_authorizer))
        kernel.submit_request(self._req(candidate_regions=["india"], allowed_regions=["india"]), self._ctx(), conn)
        assert calls == [("tenant-a", "india")]  # read-only query, no other interaction

    def test_scenario_10_fail_closed_without_resolver_never_trusts_caller_alone(self, conn):
        """No resolver wired at all -- P7C.8 must refuse rather than trusting a
        caller-only region claim (this is the core Blocker-1 fix)."""
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_strategy_generation_producer(None), capability="strategy_generation")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(self._req(candidate_regions=["india"], allowed_regions=["india"]), self._ctx(), conn)

    def test_no_resolver_and_no_constraints_still_works_unrestricted(self, conn):
        """Pure objective-ranking requests that never assert residency at all
        must keep working without a resolver -- no unrelated regression."""
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_strategy_generation_producer(None), capability="strategy_generation")
        artifact = kernel.submit_request(self._req(objective="FASTEST"), self._ctx(), conn)
        assert artifact.result["optimization"]["alternatives"]
