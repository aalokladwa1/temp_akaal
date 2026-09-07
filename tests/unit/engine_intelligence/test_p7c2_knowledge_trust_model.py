"""tests/unit/engine_intelligence/test_p7c2_knowledge_trust_model.py
=======================================================================
P7C.2 Migration Knowledge + Trust Model: trust ordering, conflict resolution,
secret redaction, and real projection over an actual CanonicalSchemaModel and the
live ProviderCatalog singleton (not a mock).
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.intelligence.knowledge.facts import KnowledgeFact, merge_facts
from akaalEngine.intelligence.knowledge.projection import (
    ProviderCapabilityKnowledgeProjector,
    SchemaKnowledgeProjector,
)
from akaalEngine.intelligence.knowledge.trust import TrustLevel, higher_trust, outranks, rank
from akaalEngine.schema.models.constraints import CanonicalForeignKey, CanonicalPrimaryKey
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _int_type() -> CanonicalType:
    return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER")


def _lob_type() -> CanonicalType:
    return CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type="CLOB")


class TestTrustOrdering:
    def test_t0_outranks_t5(self):
        assert outranks(TrustLevel.T0_CANONICAL_RUNTIME_TRUTH, TrustLevel.T5_MODEL_GENERATED_CONTENT)

    def test_t5_never_outranks_t0(self):
        assert not outranks(TrustLevel.T5_MODEL_GENERATED_CONTENT, TrustLevel.T0_CANONICAL_RUNTIME_TRUTH)

    def test_rank_strictly_increasing_t0_to_t5(self):
        levels = list(TrustLevel)
        ranks = [rank(l) for l in levels]
        assert ranks == sorted(ranks)

    def test_higher_trust_picks_canonical_over_model_generated(self):
        assert higher_trust(TrustLevel.T5_MODEL_GENERATED_CONTENT, TrustLevel.T0_CANONICAL_RUNTIME_TRUTH) == TrustLevel.T0_CANONICAL_RUNTIME_TRUTH
        assert higher_trust(TrustLevel.T1_CANONICAL_DERIVED_FACT, TrustLevel.T5_MODEL_GENERATED_CONTENT) == TrustLevel.T1_CANONICAL_DERIVED_FACT


class TestFactConflictResolution:
    def _fact(self, key, value, trust, subject_id="plan-1", retrieved_at="2026-01-01T00:00:00+00:00"):
        return KnowledgeFact(
            key=key,
            value=value,
            trust_level=trust,
            source_class="test.source",
            source_id="src-1",
            tenant_id="tenant-a",
            subject_type="migration_plan",
            subject_id=subject_id,
            retrieved_at=retrieved_at,
        )

    def test_hostile_model_generated_fact_cannot_override_canonical_fact(self):
        """Hostile test: a model-generated 'fact' claiming a table is safe to migrate
        must never override a canonical derived fact saying otherwise, even if the
        model-generated fact was retrieved more recently."""
        canonical = self._fact("safe_to_migrate", False, TrustLevel.T1_CANONICAL_DERIVED_FACT, retrieved_at="2026-01-01T00:00:00+00:00")
        model_claim = self._fact("safe_to_migrate", True, TrustLevel.T5_MODEL_GENERATED_CONTENT, retrieved_at="2026-06-01T00:00:00+00:00")
        merged = merge_facts([canonical, model_claim])
        assert len(merged) == 1
        assert merged[0].value is False
        assert merged[0].trust_level == TrustLevel.T1_CANONICAL_DERIVED_FACT

    def test_equal_trust_ties_break_on_freshness(self):
        older = self._fact("x", 1, TrustLevel.T2_ORGANIZATION_AUTHORIZED_KNOWLEDGE, retrieved_at="2026-01-01T00:00:00+00:00")
        newer = self._fact("x", 2, TrustLevel.T2_ORGANIZATION_AUTHORIZED_KNOWLEDGE, retrieved_at="2026-02-01T00:00:00+00:00")
        merged = merge_facts([older, newer])
        assert merged[0].value == 2

    def test_distinct_subjects_never_collide(self):
        f1 = self._fact("x", 1, TrustLevel.T1_CANONICAL_DERIVED_FACT, subject_id="plan-1")
        f2 = self._fact("x", 2, TrustLevel.T1_CANONICAL_DERIVED_FACT, subject_id="plan-2")
        merged = merge_facts([f1, f2])
        assert len(merged) == 2


class TestSecretRedaction:
    def test_hostile_secret_like_value_is_redacted_before_storage(self):
        fact = KnowledgeFact(
            key="connection_hint",
            value="postgres://admin:SuperSecretPass123@db.internal:5432/prod",
            trust_level=TrustLevel.T4_UNTRUSTED_USER_OR_DATA_CONTENT,
            source_class="test.source",
            source_id="src-1",
            tenant_id="tenant-a",
            subject_type="migration_plan",
            subject_id="plan-1",
        )
        assert "SuperSecretPass123" not in fact.value

    def test_nested_secret_in_list_value_is_redacted(self):
        fact = KnowledgeFact(
            key="notes",
            value=["see mysql://root:hunter2@host/db for details"],
            trust_level=TrustLevel.T4_UNTRUSTED_USER_OR_DATA_CONTENT,
            source_class="test.source",
            source_id="src-1",
            tenant_id="tenant-a",
            subject_type="migration_plan",
            subject_id="plan-1",
        )
        assert "hunter2" not in fact.value[0]

    def test_empty_tenant_id_rejected(self):
        with pytest.raises(ValueError):
            KnowledgeFact(
                key="x",
                value=1,
                trust_level=TrustLevel.T1_CANONICAL_DERIVED_FACT,
                source_class="test.source",
                source_id="src-1",
                tenant_id="",
                subject_type="migration_plan",
                subject_id="plan-1",
            )


class TestSchemaKnowledgeProjection:
    def _model(self) -> CanonicalSchemaModel:
        pk_table = CanonicalTable(
            table_name="orders",
            schema_name="public",
            columns=(
                CanonicalColumn(name="id", ordinal_position=1, source_native_type="INTEGER", canonical_type=_int_type()),
                CanonicalColumn(name="notes", ordinal_position=2, source_native_type="CLOB", canonical_type=_lob_type(), is_lob=True),
            ),
            primary_key=CanonicalPrimaryKey(name="pk_orders", table_name="orders", columns=("id",)),
            foreign_keys=(
                CanonicalForeignKey(
                    name="fk_customer",
                    table_name="orders",
                    columns=("customer_id",),
                    referenced_schema="public",
                    referenced_table="customers",
                    referenced_columns=("id",),
                ),
            ),
        )
        no_pk_table = CanonicalTable(
            table_name="staging_events",
            schema_name="public",
            columns=(
                CanonicalColumn(name="payload", ordinal_position=1, source_native_type="TEXT", canonical_type=_int_type()),
            ),
        )
        return CanonicalSchemaModel(
            model_id="model-1",
            source_vendor="postgresql",
            tables=(pk_table, no_pk_table),
        )

    def test_projection_reflects_real_model_structure(self):
        model = self._model()
        facts = SchemaKnowledgeProjector.project(model, tenant_id="tenant-a", subject_id="plan-1", source_version="v1")
        by_key = {f.key: f for f in facts}
        assert by_key["schema.table_count"].value == 2
        assert by_key["schema.total_columns"].value == 3
        assert by_key["schema.total_foreign_keys"].value == 1
        assert by_key["schema.tables_without_primary_key"].value == ["public.staging_events"]
        assert by_key["schema.lob_columns"].value == ["public.orders.notes"]

    def test_all_projected_facts_are_t1_canonical_derived(self):
        facts = SchemaKnowledgeProjector.project(self._model(), tenant_id="tenant-a", subject_id="plan-1")
        assert all(f.trust_level == TrustLevel.T1_CANONICAL_DERIVED_FACT for f in facts)

    def test_empty_model_yields_zero_counts_not_an_error(self):
        empty_model = CanonicalSchemaModel(model_id="model-empty", source_vendor="postgresql")
        facts = SchemaKnowledgeProjector.project(empty_model, tenant_id="tenant-a", subject_id="plan-empty")
        by_key = {f.key: f for f in facts}
        assert by_key["schema.table_count"].value == 0


class TestProviderCapabilityProjection:
    def test_registered_provider_yields_t0_and_t1_facts(self):
        # postgresql is one of the 49 canonical built-in providers (progress.md §41.5).
        facts = ProviderCapabilityKnowledgeProjector.project(default_provider_catalog, "postgresql", tenant_id="tenant-a")
        by_key = {f.key: f for f in facts}
        assert by_key["provider.is_registered"].value is True
        assert by_key["provider.is_registered"].trust_level == TrustLevel.T0_CANONICAL_RUNTIME_TRUTH
        assert by_key["provider.vendor_name"].trust_level == TrustLevel.T1_CANONICAL_DERIVED_FACT

    def test_unregistered_provider_yields_only_negative_t0_fact_no_fabrication(self):
        facts = ProviderCapabilityKnowledgeProjector.project(
            default_provider_catalog, "definitely-not-a-real-provider", tenant_id="tenant-a"
        )
        assert len(facts) == 1
        assert facts[0].key == "provider.is_registered"
        assert facts[0].value is False
