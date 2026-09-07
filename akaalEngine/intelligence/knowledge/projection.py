"""akaalEngine.intelligence.knowledge.projection
=================================================
Typed knowledge projectors over canonical AKAAL state (P7C brief §P7C.2). Each
projector is a pure, read-only function: it takes an already-produced canonical
object (a CanonicalSchemaModel the schema authority produced, the live provider
catalog singleton) and emits typed, trust-classified KnowledgeFact records. No
projector here performs discovery, mutates schema/connection state, or becomes a
second authority for anything it reads.
"""

from __future__ import annotations

from typing import Any, List, Optional

from akaalEngine.intelligence.knowledge.facts import KnowledgeFact
from akaalEngine.intelligence.knowledge.trust import TrustLevel


class SchemaKnowledgeProjector:
    """Projects structural facts from a canonical schema model (the schema
    authority's own output -- akaalEngine.schema.models.schema.CanonicalSchemaModel)."""

    SOURCE_CLASS = "akaalEngine.schema.models.schema.CanonicalSchemaModel"

    @classmethod
    def project(
        cls,
        model: Any,
        *,
        tenant_id: str,
        subject_id: str,
        source_version: str = "unknown",
    ) -> List[KnowledgeFact]:
        facts: List[KnowledgeFact] = []

        def _fact(key: str, value: Any) -> KnowledgeFact:
            return KnowledgeFact(
                key=key,
                value=value,
                trust_level=TrustLevel.T1_CANONICAL_DERIVED_FACT,
                source_class=cls.SOURCE_CLASS,
                source_id=subject_id,
                source_version=source_version,
                tenant_id=tenant_id,
                subject_type="schema_model",
                subject_id=subject_id,
            )

        tables = list(getattr(model, "tables", ()) or ())
        views = list(getattr(model, "views", ()) or ())
        routines = list(getattr(model, "routines", ()) or ())
        sequences = list(getattr(model, "sequences", ()) or ())

        facts.append(_fact("schema.table_count", len(tables)))
        facts.append(_fact("schema.view_count", len(views)))
        facts.append(_fact("schema.routine_count", len(routines)))
        facts.append(_fact("schema.sequence_count", len(sequences)))

        total_columns = 0
        total_fks = 0
        tables_without_pk: List[str] = []
        lob_columns: List[str] = []

        for tbl in tables:
            columns = list(getattr(tbl, "columns", ()) or ())
            total_columns += len(columns)
            total_fks += len(getattr(tbl, "foreign_keys", ()) or ())
            if getattr(tbl, "primary_key", None) is None:
                tables_without_pk.append(getattr(tbl, "qualified_name", getattr(tbl, "table_name", "")))
            for col in columns:
                if getattr(col, "is_lob", False):
                    qname = getattr(tbl, "qualified_name", getattr(tbl, "table_name", ""))
                    lob_columns.append(f"{qname}.{getattr(col, 'name', '')}")

        facts.append(_fact("schema.total_columns", total_columns))
        facts.append(_fact("schema.total_foreign_keys", total_fks))
        facts.append(_fact("schema.tables_without_primary_key", sorted(tables_without_pk)))
        facts.append(_fact("schema.lob_columns", sorted(lob_columns)))

        return facts


class ProviderCapabilityKnowledgeProjector:
    """Projects facts from the live, in-process ProviderCatalog singleton (the same
    `default_provider_catalog` every connector-facing subsystem already consults --
    never a duplicate registry)."""

    SOURCE_CLASS = "akaalEngine.connection.catalog.provider_catalog.ProviderCatalog"

    @classmethod
    def project(cls, catalog: Any, provider_id: str, *, tenant_id: str) -> List[KnowledgeFact]:
        facts: List[KnowledgeFact] = []
        is_registered = catalog.is_provider_registered(provider_id)

        # T0: the literal current in-process registration state IS the runtime
        # truth being observed right now -- there is nothing more canonical to
        # derive it from.
        facts.append(
            KnowledgeFact(
                key="provider.is_registered",
                value=is_registered,
                trust_level=TrustLevel.T0_CANONICAL_RUNTIME_TRUTH,
                source_class=cls.SOURCE_CLASS,
                source_id=provider_id,
                tenant_id=tenant_id,
                subject_type="provider",
                subject_id=provider_id,
            )
        )
        if not is_registered:
            return facts

        manifest = catalog.describe_provider(provider_id)
        # T1: the manifest is a static declaration bundled with the provider
        # strategy -- a canonical derived fact, but not itself independently
        # runtime-verified per connection (that would require a live connection
        # test, which is EXTERNAL_DEFERRED without live target infrastructure).
        for key, value in (
            ("provider.vendor_name", getattr(manifest, "vendor_name", None)),
            ("provider.family", str(getattr(manifest, "family", None))),
            ("provider.version", getattr(manifest, "provider_version", None)),
        ):
            facts.append(
                KnowledgeFact(
                    key=key,
                    value=value,
                    trust_level=TrustLevel.T1_CANONICAL_DERIVED_FACT,
                    source_class=cls.SOURCE_CLASS,
                    source_id=provider_id,
                    source_version=str(getattr(manifest, "provider_version", "unknown")),
                    tenant_id=tenant_id,
                    subject_type="provider",
                    subject_id=provider_id,
                )
            )
        return facts
