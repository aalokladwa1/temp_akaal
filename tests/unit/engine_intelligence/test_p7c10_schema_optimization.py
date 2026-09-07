"""tests/unit/engine_intelligence/test_p7c10_schema_optimization.py
=======================================================================
P7C.10 Schema & Data Model Optimization: redundant-index detection, missing-FK-
covering-index detection, classification taxonomy, and capability-aware filtering
(never recommend a feature the target provider does not support).
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.schema_optimization import (
    OptimizationClassification,
    detect_missing_fk_covering_index,
    detect_redundant_indexes,
    make_schema_optimization_producer,
)
from akaalEngine.schema.models.constraints import CanonicalForeignKey, CanonicalPrimaryKey
from akaalEngine.schema.models.indexes import CanonicalIndex
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _int_col(name: str) -> CanonicalColumn:
    return CanonicalColumn(
        name=name, ordinal_position=1, source_native_type="INTEGER",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER"),
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


class TestRedundantIndexDetection:
    def test_prefix_index_flagged_redundant(self):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"), _int_col("status")),
            indexes=(
                CanonicalIndex(name="idx_customer", table_name="orders", columns=("customer_id",)),
                CanonicalIndex(name="idx_customer_status", table_name="orders", columns=("customer_id", "status")),
            ),
        )
        recs = detect_redundant_indexes(table)
        assert len(recs) == 1
        assert recs[0].classification == OptimizationClassification.OPTIONAL_TARGET_OPTIMIZATION
        assert "idx_customer" in recs[0].description

    def test_unique_index_never_flagged_even_if_prefix(self):
        """Dropping a unique constraint changes semantics -- must never be
        proposed as a pure optimization."""
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"),),
            indexes=(
                CanonicalIndex(name="uq_customer", table_name="orders", columns=("customer_id",), is_unique=True),
                CanonicalIndex(name="idx_customer_status", table_name="orders", columns=("customer_id", "status")),
            ),
        )
        recs = detect_redundant_indexes(table)
        assert recs == []

    def test_non_overlapping_indexes_not_flagged(self):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("a"), _int_col("b")),
            indexes=(
                CanonicalIndex(name="idx_a", table_name="orders", columns=("a",)),
                CanonicalIndex(name="idx_b", table_name="orders", columns=("b",)),
            ),
        )
        assert detect_redundant_indexes(table) == []


class TestMissingFKCoveringIndex:
    def test_uncovered_fk_column_flagged(self):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"),),
            foreign_keys=(
                CanonicalForeignKey(
                    name="fk_customer", table_name="orders", columns=("customer_id",),
                    referenced_schema="public", referenced_table="customers", referenced_columns=("id",),
                ),
            ),
        )
        recs = detect_missing_fk_covering_index(table)
        assert len(recs) == 1
        assert "customer_id" in recs[0].description

    def test_covered_fk_column_not_flagged(self):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"),),
            foreign_keys=(
                CanonicalForeignKey(
                    name="fk_customer", table_name="orders", columns=("customer_id",),
                    referenced_schema="public", referenced_table="customers", referenced_columns=("id",),
                ),
            ),
            indexes=(CanonicalIndex(name="idx_customer", table_name="orders", columns=("customer_id",)),),
        )
        assert detect_missing_fk_covering_index(table) == []

    def test_fk_column_covered_by_primary_key_not_flagged(self):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"),),
            primary_key=CanonicalPrimaryKey(name="pk_orders", table_name="orders", columns=("customer_id",)),
            foreign_keys=(
                CanonicalForeignKey(
                    name="fk_customer", table_name="orders", columns=("customer_id",),
                    referenced_schema="public", referenced_table="customers", referenced_columns=("id",),
                ),
            ),
        )
        assert detect_missing_fk_covering_index(table) == []


class TestCapabilityAwareFiltering:
    def test_hostile_never_recommends_unsupported_target_feature(self):
        """If the target provider doesn't support secondary indexes at all, the
        optimization must not be recommended -- capability awareness beats a
        generically-appealing recommendation."""
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"),),
            foreign_keys=(
                CanonicalForeignKey(
                    name="fk_customer", table_name="orders", columns=("customer_id",),
                    referenced_schema="public", referenced_table="customers", referenced_columns=("id",),
                ),
            ),
        )
        model = CanonicalSchemaModel(model_id="m1", source_vendor="postgresql", tables=(table,))
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(
            IntelligenceTask.OPTIMIZE,
            make_schema_optimization_producer(lambda r, c: model, provider_capability_checker=lambda feature: False),
            capability="schema_optimization",
        )
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE intelligence_artifacts (artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, "
            "workspace_id TEXT, project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL, "
            "subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL, "
            "policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL, fingerprint TEXT NOT NULL, "
            "result TEXT NOT NULL, lifecycle_state TEXT NOT NULL, created_at TEXT NOT NULL, requested_by TEXT NOT NULL, "
            "model_provider TEXT, model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT)"
        )
        req = IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1", capability="schema_optimization",
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["recommendations"] == []
        conn.close()


class TestEndToEndProducer:
    def test_producer_via_kernel(self, conn):
        table = CanonicalTable(
            table_name="orders", schema_name="public", columns=(_int_col("customer_id"), _int_col("status")),
            indexes=(
                CanonicalIndex(name="idx_customer", table_name="orders", columns=("customer_id",)),
                CanonicalIndex(name="idx_customer_status", table_name="orders", columns=("customer_id", "status")),
            ),
        )
        model = CanonicalSchemaModel(model_id="m1", source_vendor="postgresql", tables=(table,))
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_schema_optimization_producer(lambda r, c: model), capability="schema_optimization")
        req = IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1", capability="schema_optimization",
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["epistemic_type"] == "RECOMMENDATION"
        assert len(artifact.result["findings"]) == 1
