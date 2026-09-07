"""tests/unit/engine_intelligence/test_p7c11_sql_translation.py
===================================================================
P7C.11 Semantic SQL/DB Logic Translation & Verification (DDL scope): real
DDLGenerator-backed translation, certification aggregation from real per-statement
ConversionSafety, adversarial type semantics, and honest procedural-scope boundary
reporting (never silently drops unsupported procedural objects).
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.sql_translation import (
    TranslationCertification,
    certify_package,
    make_sql_translation_producer,
)
from akaalEngine.schema.ddl.emitter import DDLStage, StructuredDDLArtifact
from akaalEngine.schema.models.programmables import CanonicalRoutine
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _artifact(safety, warnings=()) -> StructuredDDLArtifact:
    return StructuredDDLArtifact(
        object_type="TABLE", object_name="t", schema_name="public", sql="CREATE TABLE t (id INT);",
        target_engine="postgresql", stage=DDLStage.TABLES, safety=safety, warnings=warnings,
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


def _kernel(producer) -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.CONVERT, producer, capability="sql_translation")
    return kernel


def _req(*, subject_id="plan-1", **params) -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.CONVERT, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id=subject_id, subject_version="v1", requested_by="user-1", parameters=params,
        capability="sql_translation",
    )


def _ctx() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")


class TestCertificationAggregation:
    from akaalEngine.schema.models.types import ConversionSafety

    def test_all_exact_yields_exact_translation_proven(self):
        from akaalEngine.schema.models.types import ConversionSafety
        assert certify_package([_artifact(ConversionSafety.EXACT), _artifact(ConversionSafety.EXACT)]) == TranslationCertification.EXACT_TRANSLATION_PROVEN

    def test_single_lossy_statement_forces_manual_review_overall(self):
        from akaalEngine.schema.models.types import ConversionSafety
        artifacts = [_artifact(ConversionSafety.EXACT), _artifact(ConversionSafety.LOSSY)]
        assert certify_package(artifacts) == TranslationCertification.MANUAL_REVIEW_REQUIRED

    def test_single_unsupported_statement_forces_unsupported_overall(self):
        from akaalEngine.schema.models.types import ConversionSafety
        artifacts = [_artifact(ConversionSafety.EXACT), _artifact(ConversionSafety.UNSUPPORTED)]
        assert certify_package(artifacts) == TranslationCertification.UNSUPPORTED

    def test_hostile_never_claims_exact_when_any_statement_is_worse(self):
        """Hostile: certification must never be optimistic -- one bad statement
        among a hundred good ones still drags the whole package down."""
        from akaalEngine.schema.models.types import ConversionSafety
        artifacts = [_artifact(ConversionSafety.EXACT) for _ in range(99)] + [_artifact(ConversionSafety.UNSUPPORTED)]
        assert certify_package(artifacts) == TranslationCertification.UNSUPPORTED

    def test_empty_package_is_trivially_exact(self):
        assert certify_package([]) == TranslationCertification.EXACT_TRANSLATION_PROVEN


class TestEndToEndProducer:
    def _clean_model(self) -> CanonicalSchemaModel:
        table = CanonicalTable(
            table_name="customers", schema_name="public",
            columns=(CanonicalColumn(
                name="id", ordinal_position=1, source_native_type="INTEGER",
                canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER"),
            ),),
        )
        return CanonicalSchemaModel(model_id="m-clean", source_vendor="postgresql", tables=(table,))

    def _risky_model(self) -> CanonicalSchemaModel:
        table = CanonicalTable(
            table_name="places", schema_name="public",
            columns=(
                CanonicalColumn(name="id", ordinal_position=1, source_native_type="INTEGER", canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER")),
                CanonicalColumn(name="geo", ordinal_position=2, source_native_type="GEOMETRY", canonical_type=CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type="GEOMETRY")),
            ),
        )
        return CanonicalSchemaModel(model_id="m-risky", source_vendor="oracle", tables=(table,))

    def test_clean_model_translation_produces_sql_and_certification(self, conn):
        kernel = _kernel(make_sql_translation_producer(lambda r, c: self._clean_model()))
        artifact = kernel.submit_request(_req(target_engine="postgresql"), _ctx(), conn)
        assert artifact.result["data"]["statement_count"] > 0
        assert len(artifact.result["data"]["ddl_sql"]) > 0
        assert artifact.result["data"]["certification"] == TranslationCertification.EXACT_TRANSLATION_PROVEN.value

    def test_unsupported_type_lowers_certification_and_produces_finding(self, conn):
        kernel = _kernel(make_sql_translation_producer(lambda r, c: self._risky_model()))
        artifact = kernel.submit_request(_req(target_engine="mysql", subject_id="plan-risky"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-risky", subject_version="v1"
        ), conn)
        assert artifact.result["data"]["certification"] == TranslationCertification.UNSUPPORTED.value
        codes = [f["code"] for f in artifact.result["findings"]]
        assert any("UNSUPPORTED" in c for c in codes)

    def test_missing_target_engine_raises(self, conn):
        kernel = _kernel(make_sql_translation_producer(lambda r, c: self._clean_model()))
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_req(), _ctx(), conn)

    def test_routine_with_no_source_definition_reported_not_silently_dropped(self, conn):
        routine = CanonicalRoutine(name="calc_total", schema_name="public")
        model = CanonicalSchemaModel(model_id="m-proc", source_vendor="oracle", routines=(routine,))
        kernel = _kernel(make_sql_translation_producer(lambda r, c: model))
        artifact = kernel.submit_request(_req(target_engine="postgresql", subject_id="plan-proc"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-proc", subject_version="v1"
        ), conn)
        codes = [f["code"] for f in artifact.result["findings"]]
        assert "SQL_TRANSLATION:PROCEDURAL_SOURCE_MISSING" in codes

    def test_oracle_plsql_routine_genuinely_translated_to_postgresql(self, conn):
        """Real end-to-end procedural translation: Oracle PL/SQL source ->
        PLSQLParser -> PLpgSQLEmitter -> emitted PL/pgSQL, reachable through the
        full IntelligenceKernel producer pathway."""
        routine = CanonicalRoutine(
            name="calc_total", schema_name="public",
            definition_sql="CREATE OR REPLACE PROCEDURE calc_total(p_id IN NUMBER, p_total OUT NUMBER) IS "
            "BEGIN SELECT SUM(amount) INTO p_total FROM orders WHERE customer_id = p_id; END;",
        )
        model = CanonicalSchemaModel(model_id="m-proc-ok", source_vendor="oracle", routines=(routine,))
        kernel = _kernel(make_sql_translation_producer(lambda r, c: model))
        artifact = kernel.submit_request(_req(target_engine="postgresql", subject_id="plan-proc-ok"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-proc-ok", subject_version="v1"
        ), conn)
        assert artifact.result["data"]["routines_translated"] == 1
        emitted = artifact.result["data"]["routine_translation_sql"]
        assert "public.calc_total" in emitted
        assert "plpgsql" in emitted["public.calc_total"].lower()
        # Clean transpile is capped, never claimed EXACT/SEMANTIC_EQUIVALENCE.
        assert artifact.result["data"]["certification"] == TranslationCertification.COMPILES_BUT_EQUIVALENCE_UNPROVEN.value

    def test_hostile_untranslated_tsql_variable_syntax_caught_by_static_check(self, conn):
        """Hostile: a T-SQL '@variable' surviving verbatim into emitted PL/pgSQL
        is invalid Postgres syntax. The existing procedural engine's own
        diagnostics do NOT catch this (verified during scope reconciliation) --
        this producer's own static soundness check must catch it and force
        MANUAL_REVIEW_REQUIRED rather than presenting a broken translation as
        clean."""
        routine = CanonicalRoutine(
            name="calc_total", schema_name="public",
            definition_sql="CREATE PROCEDURE calc_total @id INT, @total INT OUTPUT AS BEGIN "
            "SELECT @total = SUM(amount) FROM orders WHERE customer_id = @id; END",
        )
        model = CanonicalSchemaModel(model_id="m-proc-tsql", source_vendor="mssql", routines=(routine,))
        kernel = _kernel(make_sql_translation_producer(lambda r, c: model))
        artifact = kernel.submit_request(_req(target_engine="postgresql", subject_id="plan-proc-tsql"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-proc-tsql", subject_version="v1"
        ), conn)
        codes = [f["code"] for f in artifact.result["findings"]]
        assert "SQL_TRANSLATION:PROCEDURAL_STATIC_CHECK_FAILED" in codes
        assert artifact.result["data"]["certification"] == TranslationCertification.MANUAL_REVIEW_REQUIRED.value

    def test_unsupported_source_target_dialect_combo_reported_honestly(self, conn):
        routine = CanonicalRoutine(
            name="calc_total", schema_name="public", definition_sql="CREATE PROCEDURE calc_total() BEGIN END",
        )
        model = CanonicalSchemaModel(model_id="m-proc-unsupported", source_vendor="db2", routines=(routine,))
        kernel = _kernel(make_sql_translation_producer(lambda r, c: model))
        artifact = kernel.submit_request(_req(target_engine="postgresql", subject_id="plan-proc-unsupported"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-proc-unsupported", subject_version="v1"
        ), conn)
        codes = [f["code"] for f in artifact.result["findings"]]
        assert "SQL_TRANSLATION:PROCEDURAL_DIALECT_UNSUPPORTED" in codes
        assert artifact.result["data"]["certification"] == TranslationCertification.UNSUPPORTED.value

    def test_triggers_and_packages_still_honestly_reported_unsupported(self, conn):
        from akaalEngine.schema.models.programmables import CanonicalTrigger

        trigger = CanonicalTrigger(name="trg_audit", schema_name="public", table_name="orders")
        model = CanonicalSchemaModel(model_id="m-trigger", source_vendor="oracle", triggers=(trigger,))
        kernel = _kernel(make_sql_translation_producer(lambda r, c: model))
        artifact = kernel.submit_request(_req(target_engine="postgresql", subject_id="plan-trigger"), IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-trigger", subject_version="v1"
        ), conn)
        codes = [f["code"] for f in artifact.result["findings"]]
        assert "SQL_TRANSLATION:UNSUPPORTED_IN_THIS_SCOPE" in codes
        assert any("differential execution" in m for m in artifact.result["confidence_evidence"]["missing_information"])

    @pytest.mark.parametrize("target_engine", ["postgresql", "mysql", "sqlite", "snowflake"])
    def test_multiple_target_dialects_all_produce_valid_certification(self, conn, target_engine):
        kernel = _kernel(make_sql_translation_producer(lambda r, c: self._clean_model()))
        artifact = kernel.submit_request(
            _req(target_engine=target_engine, subject_id=f"plan-{target_engine}"),
            IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id=f"plan-{target_engine}", subject_version="v1"),
            conn,
        )
        assert artifact.result["data"]["certification"] in [c.value for c in TranslationCertification]
