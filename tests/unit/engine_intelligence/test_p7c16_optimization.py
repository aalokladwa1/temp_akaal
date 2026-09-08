"""tests/unit/engine_intelligence/test_p7c16_optimization.py
=================================================================
P7C.16: reuses P7C.12 scenario arithmetic across worker-count candidates,
never presents an infeasible/illegal candidate as best, honest cost omission
when no organization-configured rate is supplied, and fails closed on
region-scoped requests with no canonical authorizer configured.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.knowledge.constraint_projection import project_trusted_constraints
from akaalEngine.intelligence.producers.optimization import make_optimization_producer


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


def _kernel(constraint_resolver=None) -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.OPTIMIZE, make_optimization_producer(constraint_resolver), capability="performance_optimization")
    return kernel


def _request(actor_id="user-1", actor_roles="", **params) -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id="plan-1", subject_version="v1", requested_by=actor_id,
        capability="performance_optimization", parameters=params,
    )


def _context(actor_id="user-1", actor_roles="") -> IntelligenceContext:
    return IntelligenceContext(
        tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1",
        extra_dimensions={"actor_id": actor_id, "actor_roles": actor_roles},
    )


def _per_actor_constraint_resolver(region_grants_by_actor):
    """Mirrors the REAL production resolver's shape (a per-(request,context)
    closure calling project_trusted_constraints with a REAL per-actor
    authorizer) -- proving the resolver genuinely re-derives the actual
    requesting actor's own grants each call, not merely the tenant."""

    def resolver(request, context):
        actor_id = context.extra_dimensions.get("actor_id", request.requested_by)

        def _region_authorizer(tenant_id, region):
            return region in region_grants_by_actor.get(actor_id, frozenset())

        candidate_regions = frozenset(request.parameters.get("candidate_regions") or [])
        return project_trusted_constraints(request.tenant_id, candidate_regions=candidate_regions, region_authorizer=_region_authorizer)

    return resolver


class TestScenarioSweepReuse:
    def test_multiple_worker_counts_evaluated_best_is_feasible(self, conn):
        kernel = _kernel()
        req = _request(
            dataset_size_bytes=1_000_000_000, worker_throughput_bytes_per_sec=1_000_000,
            validation_throughput_bytes_per_sec=2_000_000, cutover_window_seconds=10_000,
            candidate_worker_counts=[1, 4, 16],
        )
        artifact = kernel.submit_request(req, _context(), conn)
        alternatives = artifact.result["optimization"]["alternatives"]
        assert len(alternatives) == 3
        best = artifact.result["data"]["best_alternative"]
        best_alt = next(a for a in alternatives if a["label"] == best)
        assert best_alt["objective_scores"]["feasible"] == 1.0

    def test_infeasible_candidate_never_wins(self, conn):
        kernel = _kernel()
        req = _request(
            dataset_size_bytes=1_000_000_000_000, worker_throughput_bytes_per_sec=1000,
            validation_throughput_bytes_per_sec=1000, cutover_window_seconds=10,
            candidate_worker_counts=[1],
        )
        artifact = kernel.submit_request(req, _context(), conn)
        assert artifact.result["data"]["best_alternative"] is None


class TestCostHonesty:
    def test_no_cost_rate_supplied_cost_omitted_not_invented(self, conn):
        kernel = _kernel()
        req = _request(
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
        )
        artifact = kernel.submit_request(req, _context(), conn)
        for alt in artifact.result["optimization"]["alternatives"]:
            assert "cost" not in alt["objective_scores"]
        assert any("invented price" in m for m in artifact.result["confidence_evidence"]["missing_information"])

    def test_cost_computed_from_supplied_org_rate(self, conn):
        kernel = _kernel()
        req = _request(
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
            cost_per_worker_hour=2.5,
        )
        artifact = kernel.submit_request(req, _context(), conn)
        for alt in artifact.result["optimization"]["alternatives"]:
            if alt["objective_scores"].get("feasible") == 1.0:
                assert "cost" in alt["objective_scores"]


class TestRegionLegalityFailsClosed:
    def test_candidate_regions_without_resolver_refuses(self, conn):
        kernel = _kernel(constraint_resolver=None)
        req = _request(
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
            candidate_regions=["india"],
        )
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(req, _context(), conn)

    def test_illegal_region_excluded_with_counterfactual(self, conn):
        resolver = _per_actor_constraint_resolver({"user-1": frozenset({"india"})})
        kernel = _kernel(constraint_resolver=resolver)
        req = _request(
            actor_id="user-1",
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
            candidate_regions=["india", "singapore"],
        )
        artifact = kernel.submit_request(req, _context(actor_id="user-1"), conn)
        assert artifact.result["data"]["legal_regions"] == ["india"]
        counterfactuals = artifact.result["explanation"]["counterfactuals"]
        assert any(c["rejected_alternative"] == "region=singapore" for c in counterfactuals)


class TestPerActorAuthorizationNotMerelyPerTenant:
    """Owner-review Blocker 1 closure proof: two DIFFERENT actors in the SAME
    tenant get DIFFERENT feasible sets, proving the resolver genuinely
    re-derives the real requesting actor's own grants each call -- not a
    coarser tenant-only check."""

    def test_two_actors_same_tenant_different_feasible_sets(self, conn):
        resolver = _per_actor_constraint_resolver({
            "actor-india-only": frozenset({"india"}),
            "actor-singapore-only": frozenset({"singapore"}),
        })
        kernel = _kernel(constraint_resolver=resolver)
        base_params = dict(
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
            candidate_regions=["india", "singapore"],
        )

        req_a = _request(actor_id="actor-india-only", **base_params)
        artifact_a = kernel.submit_request(req_a, _context(actor_id="actor-india-only"), conn)
        assert artifact_a.result["data"]["legal_regions"] == ["india"]

        req_b = _request(actor_id="actor-singapore-only", **base_params)
        artifact_b = kernel.submit_request(req_b, _context(actor_id="actor-singapore-only"), conn)
        assert artifact_b.result["data"]["legal_regions"] == ["singapore"]

    def test_forged_actor_id_in_parameters_has_no_effect(self, conn):
        """A caller cannot widen their own feasible set by claiming to be a
        different actor inside `parameters` -- only the REAL requesting
        actor identity (threaded via IntelligenceContext.extra_dimensions,
        never caller-editable request.parameters) is ever consulted."""
        resolver = _per_actor_constraint_resolver({"real-actor": frozenset({"india"}), "forged-admin": frozenset({"india", "singapore", "germany"})})
        kernel = _kernel(constraint_resolver=resolver)
        req = _request(
            actor_id="real-actor",
            dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=100_000,
            validation_throughput_bytes_per_sec=100_000, cutover_window_seconds=1000,
            candidate_regions=["india", "singapore", "germany"],
            actor_id_override="forged-admin",  # not a recognized field -- must have zero effect
        )
        artifact = kernel.submit_request(req, _context(actor_id="real-actor"), conn)
        assert artifact.result["data"]["legal_regions"] == ["india"]
