"""tests/unit/engine_intelligence/test_p7c9_wave_portfolio_optimization.py
==============================================================================
P7C.9 Dependency, Wave & Portfolio Optimization: real topological/SCC algorithms
(reused, not reinvented), deterministic wave layering, circular dependency
detection, and cross-migration shared-object contention.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.wave_planning import (
    compute_waves,
    detect_shared_object_contention,
    group_by_wave,
    make_portfolio_contention_producer,
    make_wave_planning_producer,
)
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.models.schema import CanonicalSchemaModel, CanonicalView
from akaalEngine.schema.models.programmables import CanonicalRoutine
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _int_col(name: str) -> CanonicalColumn:
    return CanonicalColumn(
        name=name, ordinal_position=1, source_native_type="INTEGER",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER"),
    )


def _model_with_view_dependency() -> CanonicalSchemaModel:
    table = CanonicalTable(table_name="orders", schema_name="public", columns=(_int_col("id"),))
    view = CanonicalView(
        view_name="order_summary", schema_name="public",
        view_definition="SELECT * FROM orders", dependencies=("public.orders",),
    )
    return CanonicalSchemaModel(model_id="model-v", source_vendor="postgresql", tables=(table,), views=(view,))


def _model_with_cyclic_routines() -> CanonicalSchemaModel:
    routine_a = CanonicalRoutine(name="routine_a", schema_name="public", dependencies=("routine:public.routine_b",))
    routine_b = CanonicalRoutine(name="routine_b", schema_name="public", dependencies=("routine:public.routine_a",))
    return CanonicalSchemaModel(model_id="model-cyclic", source_vendor="postgresql", routines=(routine_a, routine_b))


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


def _kernel(producer) -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.OPTIMIZE, producer, capability="wave_planning")
    return kernel


def _req(**overrides) -> IntelligenceRequest:
    base = dict(
        task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id="plan-1", subject_version="v1", requested_by="user-1", capability="wave_planning",
    )
    base.update(overrides)
    return IntelligenceRequest(**base)


def _ctx() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")


class TestWaveComputation:
    def test_view_depends_on_table_yields_later_wave(self):
        graph = MultiDomainDependencyGraph.build_from_model(_model_with_view_dependency())
        waves = compute_waves(graph)
        table_wave = waves["table:public.orders"]
        view_wave = waves["view:public.order_summary"]
        assert view_wave > table_wave

    def test_group_by_wave_produces_deterministic_sorted_groups(self):
        graph = MultiDomainDependencyGraph.build_from_model(_model_with_view_dependency())
        waves = compute_waves(graph)
        groups = group_by_wave(waves)
        assert groups == sorted(groups[i] for i in range(len(groups)))
        for group in groups:
            assert group == sorted(group)


class TestCapabilityKeyedProducerRegistry:
    def test_wave_planning_registered_under_distinct_capability(self):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        assert not kernel.has_producer(IntelligenceTask.OPTIMIZE, capability="wave_planning")
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_wave_planning_producer(lambda r, c: _model_with_view_dependency()), capability="wave_planning")
        assert kernel.has_producer(IntelligenceTask.OPTIMIZE, capability="wave_planning")
        assert not kernel.has_producer(IntelligenceTask.OPTIMIZE, capability=None)


class TestWavePlanningProducerEndToEnd:
    def test_end_to_end_via_kernel(self, conn):
        kernel = _kernel(make_wave_planning_producer(lambda r, c: _model_with_view_dependency()))
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        assert artifact.result["epistemic_type"] == "DERIVED_FACT"
        assert len(artifact.result["data"]["wave_groups"]) >= 2

    def test_circular_dependency_detected_and_reported_as_finding(self, conn):
        kernel = _kernel(make_wave_planning_producer(lambda r, c: _model_with_cyclic_routines()))
        artifact = kernel.submit_request(_req(subject_id="plan-cyclic"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-cyclic", subject_version="v1"
        ), conn)
        assert len(artifact.result["data"]["circular_dependency_groups"]) == 1
        cycle = artifact.result["data"]["circular_dependency_groups"][0]
        assert set(cycle) == {"routine:public.routine_a", "routine:public.routine_b"}
        finding_codes = [f["code"] for f in artifact.result["findings"]]
        assert "DEPENDENCY:CIRCULAR_GROUP" in finding_codes

    def test_computation_is_real_not_fabricated_different_models_different_waves(self, conn):
        kernel = _kernel(make_wave_planning_producer(lambda r, c: _model_with_view_dependency()))
        artifact1 = kernel.submit_request(_req(subject_id="p1"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="p1", subject_version="v1"
        ), conn)

        kernel2 = _kernel(make_wave_planning_producer(lambda r, c: CanonicalSchemaModel(model_id="empty", source_vendor="postgresql")))
        artifact2 = kernel2.submit_request(_req(subject_id="p2"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="p2", subject_version="v1"
        ), conn)
        assert artifact1.result["data"]["wave_groups"] != artifact2.result["data"]["wave_groups"]


class TestPortfolioContention:
    def test_shared_object_detected_across_migrations(self):
        shared_table = CanonicalTable(table_name="shared_customers", schema_name="public", columns=(_int_col("id"),))
        graph_a = MultiDomainDependencyGraph.build_from_model(
            CanonicalSchemaModel(model_id="a", source_vendor="postgresql", tables=(shared_table,))
        )
        graph_b = MultiDomainDependencyGraph.build_from_model(
            CanonicalSchemaModel(model_id="b", source_vendor="postgresql", tables=(shared_table,))
        )
        contention = detect_shared_object_contention({"mig-a": graph_a, "mig-b": graph_b})
        assert "table:public.shared_customers" in contention
        assert contention["table:public.shared_customers"] == ["mig-a", "mig-b"]

    def test_no_false_positive_contention_for_disjoint_migrations(self):
        table_a = CanonicalTable(table_name="only_in_a", schema_name="public", columns=(_int_col("id"),))
        table_b = CanonicalTable(table_name="only_in_b", schema_name="public", columns=(_int_col("id"),))
        graph_a = MultiDomainDependencyGraph.build_from_model(CanonicalSchemaModel(model_id="a", source_vendor="postgresql", tables=(table_a,)))
        graph_b = MultiDomainDependencyGraph.build_from_model(CanonicalSchemaModel(model_id="b", source_vendor="postgresql", tables=(table_b,)))
        contention = detect_shared_object_contention({"mig-a": graph_a, "mig-b": graph_b})
        # schema:public is shared by both -- that's expected/correct (same schema
        # namespace); the object-level tables must NOT show false contention.
        assert "table:public.only_in_a" not in contention
        assert "table:public.only_in_b" not in contention

    def test_portfolio_producer_end_to_end(self, conn):
        shared_table = CanonicalTable(table_name="shared_customers", schema_name="public", columns=(_int_col("id"),))
        graph_a = MultiDomainDependencyGraph.build_from_model(CanonicalSchemaModel(model_id="a", source_vendor="postgresql", tables=(shared_table,)))
        graph_b = MultiDomainDependencyGraph.build_from_model(CanonicalSchemaModel(model_id="b", source_vendor="postgresql", tables=(shared_table,)))

        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(
            IntelligenceTask.OPTIMIZE,
            make_portfolio_contention_producer(lambda r, c: {"mig-a": graph_a, "mig-b": graph_b}),
            capability="portfolio_contention",
        )
        req = IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="portfolio",
            subject_id="portfolio-1", subject_version="v1", requested_by="user-1", capability="portfolio_contention",
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="portfolio", subject_id="portfolio-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert len(artifact.result["findings"]) == 1
        assert artifact.result["findings"][0]["code"] == "PORTFOLIO:SHARED_OBJECT_CONTENTION"
