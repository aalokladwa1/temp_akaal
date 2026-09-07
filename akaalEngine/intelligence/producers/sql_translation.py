"""akaalEngine.intelligence.producers.sql_translation
=======================================================
P7C.11 -- Semantic SQL / Database Logic Translation & Verification.

Scope reconciliation (2026-09-07, closing a Group-1 freeze blocker): this
producer originally covered DDL only. On review it was found that the
repository already contains real, working, previously-unwired procedural
transpilation machinery --
  - akaalEngine.schema.procedural.parsers.plsql.PLSQLParser  (Oracle PL/SQL -> AOIR)
  - akaalEngine.schema.procedural.parsers.tsql.TSQLParser    (T-SQL -> AOIR)
  - akaalEngine.schema.procedural.emitters.plpgsql.PLpgSQLEmitter (AOIR -> PL/pgSQL)
  - akaalEngine.schema.procedural.diagnostics.ConversionState/ProceduralConversionResult
This producer now wires that machinery in for CanonicalRoutine (PROCEDURE/
FUNCTION) objects -- covering the "stored procedures; functions" bullet of the
P7C.11 brief for the two source dialects (Oracle, T-SQL) x one target dialect
(PostgreSQL/PL-pgSQL) the existing engine actually supports.

Still explicitly out of scope, honestly reported rather than fabricated:
  - TRIGGERS and PACKAGES: PLSQLParser.parse() only recognizes CREATE
    PROCEDURE/FUNCTION (verified by inspection -- it raises SyntaxError on
    anything else); no trigger/package AST entrypoint exists in this repo yet.
  - Any source dialect other than Oracle/T-SQL, or any target dialect other
    than PostgreSQL: no parser/emitter exists for them in this repository.
  - Differential (live) execution verification: EXTERNAL_DEFERRED -- no live
    database engine is available in this environment to execute source vs.
    target logic and diff results. Static verification only (see
    _looks_like_untranslated_source_syntax below).

Certification honesty: this procedural path is deliberately capped BELOW
EXACT_TRANSLATION_PROVEN/SEMANTIC_EQUIVALENCE_PROVEN even on a clean
(no-diagnostic) transpile. Reason, discovered empirically during this
reconciliation: PLpgSQLEmitter can emit T-SQL '@variable'-style identifiers
verbatim into PL/pgSQL output (which is NOT valid PostgreSQL syntax) WITHOUT
raising any diagnostic -- i.e. `ProceduralConversionResult.has_errors` is not
yet a complete correctness signal for this newer, thinly-tested path (3 unit
tests in tests/unit/engine_schema/test_aoir_ast_pipeline.py, versus the
extensively-exercised DDL engine). A real, local, deterministic static check
(_looks_like_untranslated_source_syntax) catches this specific known defect
class and forces MANUAL_REVIEW_REQUIRED when triggered; otherwise the best a
clean procedural transpile earns is COMPILES_BUT_EQUIVALENCE_UNPROVEN, never
higher, until live differential execution exists.

Each emitted DDL StructuredDDLArtifact still carries a real ConversionSafety
classification computed by the mature DDL emitter; this producer aggregates
DDL and procedural certifications and never claims a certification above the
worst of the two.
"""

from __future__ import annotations

import enum
import re
from collections import Counter
from typing import Any, List, Optional, Tuple

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.models.types import ConversionSafety


class TranslationCertification(str, enum.Enum):
    EXACT_TRANSLATION_PROVEN = "EXACT_TRANSLATION_PROVEN"
    SEMANTIC_EQUIVALENCE_PROVEN = "SEMANTIC_EQUIVALENCE_PROVEN"
    COMPILES_BUT_EQUIVALENCE_UNPROVEN = "COMPILES_BUT_EQUIVALENCE_UNPROVEN"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


# Ordered worst-to-best is NOT what we want here -- we want "does any single
# artifact's safety force the overall certification down": a mapping from the
# WORST ConversionSafety observed among a package's artifacts to the resulting
# overall TranslationCertification. This is a deterministic, total function --
# every ConversionSafety value has an explicit mapping.
_SAFETY_TO_CERTIFICATION = {
    ConversionSafety.EXACT: TranslationCertification.EXACT_TRANSLATION_PROVEN,
    ConversionSafety.SEMANTICALLY_EQUIVALENT: TranslationCertification.SEMANTIC_EQUIVALENCE_PROVEN,
    ConversionSafety.COMPATIBLE_WITH_TRANSFORMATION: TranslationCertification.COMPILES_BUT_EQUIVALENCE_UNPROVEN,
    ConversionSafety.COMPATIBILITY_LAYER_REQUIRED: TranslationCertification.COMPILES_BUT_EQUIVALENCE_UNPROVEN,
    ConversionSafety.LOSSY: TranslationCertification.MANUAL_REVIEW_REQUIRED,
    ConversionSafety.USER_DECISION_REQUIRED: TranslationCertification.MANUAL_REVIEW_REQUIRED,
    ConversionSafety.UNSUPPORTED: TranslationCertification.UNSUPPORTED,
}

# Certification severity order, worst last, used to find the single overall
# result across many artifacts (the overall certification is never better than
# the worst individual artifact's).
_CERTIFICATION_SEVERITY = [
    TranslationCertification.EXACT_TRANSLATION_PROVEN,
    TranslationCertification.SEMANTIC_EQUIVALENCE_PROVEN,
    TranslationCertification.COMPILES_BUT_EQUIVALENCE_UNPROVEN,
    TranslationCertification.MANUAL_REVIEW_REQUIRED,
    TranslationCertification.UNSUPPORTED,
]


def certify_package(artifacts) -> TranslationCertification:
    if not artifacts:
        return TranslationCertification.EXACT_TRANSLATION_PROVEN
    worst_index = 0
    for art in artifacts:
        cert = _SAFETY_TO_CERTIFICATION[art.safety]
        idx = _CERTIFICATION_SEVERITY.index(cert)
        worst_index = max(worst_index, idx)
    return _CERTIFICATION_SEVERITY[worst_index]


def _worse(a: TranslationCertification, b: TranslationCertification) -> TranslationCertification:
    ia, ib = _CERTIFICATION_SEVERITY.index(a), _CERTIFICATION_SEVERITY.index(b)
    return a if ia >= ib else b


# Deliberately narrow, deterministic static check: PostgreSQL identifiers can
# never contain '@'. A T-SQL-style '@variable' surviving verbatim into emitted
# PL/pgSQL is a concrete, real defect signature this check catches -- found by
# hostile testing during this scope reconciliation (see module docstring).
_UNTRANSLATED_TSQL_VARIABLE_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*")


def _looks_like_untranslated_source_syntax(sql: str) -> Optional[str]:
    match = _UNTRANSLATED_TSQL_VARIABLE_RE.search(sql)
    if match:
        return f"emitted SQL still contains source-dialect variable syntax {match.group(0)!r}, invalid in PostgreSQL"
    return None


def _select_procedural_parser(source_vendor: str):
    from akaalEngine.schema.procedural.parsers.plsql import PLSQLParser
    from akaalEngine.schema.procedural.parsers.tsql import TSQLParser

    v = (source_vendor or "").strip().lower()
    if v == "oracle":
        return PLSQLParser
    if v in ("mssql", "sqlserver", "sql_server"):
        return TSQLParser
    return None


def _procedural_emitter_for(target_engine: str):
    from akaalEngine.schema.procedural.emitters.plpgsql import PLpgSQLEmitter

    v = (target_engine or "").strip().lower()
    if v in ("postgresql", "postgres"):
        return PLpgSQLEmitter
    return None


def _translate_routine(routine: Any, *, source_vendor: str, target_engine: str, schema_name: str) -> Tuple[
    Optional[str], TranslationCertification, List[DiagnosticFinding]
]:
    """Attempts real procedural translation for one CanonicalRoutine. Returns
    (emitted_sql_or_None, certification_for_this_routine, findings). Never
    raises -- every failure mode becomes a typed finding instead."""
    qname = getattr(routine, "qualified_name", getattr(routine, "name", "unknown_routine"))
    parser_cls = _select_procedural_parser(source_vendor)
    emitter_cls = _procedural_emitter_for(target_engine)
    definition_sql = getattr(routine, "definition_sql", None)

    if parser_cls is None or emitter_cls is None:
        return None, TranslationCertification.UNSUPPORTED, [
            DiagnosticFinding(
                code="SQL_TRANSLATION:PROCEDURAL_DIALECT_UNSUPPORTED",
                severity="HIGH",
                message=f"{qname}: no procedural parser/emitter registered for "
                f"{source_vendor!r} -> {target_engine!r}; reported, not silently dropped.",
                evidence_refs=[qname],
            )
        ]

    if not definition_sql or not str(definition_sql).strip():
        return None, TranslationCertification.MANUAL_REVIEW_REQUIRED, [
            DiagnosticFinding(
                code="SQL_TRANSLATION:PROCEDURAL_SOURCE_MISSING",
                severity="MEDIUM",
                message=f"{qname}: no source definition_sql available to translate; cannot certify.",
                evidence_refs=[qname],
            )
        ]

    try:
        ast = parser_cls(str(definition_sql)).parse()
        result = emitter_cls.emit_routine(ast, schema_name=schema_name)
    except Exception as exc:  # noqa: BLE001 -- a parse/emit failure is data, not a producer crash
        return None, TranslationCertification.UNSUPPORTED, [
            DiagnosticFinding(
                code="SQL_TRANSLATION:PROCEDURAL_PARSE_FAILED",
                severity="HIGH",
                message=f"{qname}: procedural translation failed: {exc}",
                evidence_refs=[qname],
            )
        ]

    findings: List[DiagnosticFinding] = []
    if result.has_errors:
        for diag in result.diagnostics:
            findings.append(
                DiagnosticFinding(
                    code=f"SQL_TRANSLATION:PROCEDURAL_{diag.severity}",
                    severity="HIGH" if diag.severity in ("ERROR", "MANUAL_INTERVENTION") else "MEDIUM",
                    message=f"{qname}: {diag.message}",
                    evidence_refs=[qname],
                )
            )
        return result.target_sql, TranslationCertification.MANUAL_REVIEW_REQUIRED, findings

    static_issue = _looks_like_untranslated_source_syntax(result.target_sql)
    if static_issue:
        findings.append(
            DiagnosticFinding(
                code="SQL_TRANSLATION:PROCEDURAL_STATIC_CHECK_FAILED",
                severity="HIGH",
                message=f"{qname}: {static_issue}.",
                evidence_refs=[qname],
            )
        )
        return result.target_sql, TranslationCertification.MANUAL_REVIEW_REQUIRED, findings

    # Clean transpile, no diagnostics, passed our own static soundness check --
    # still capped at COMPILES_BUT_EQUIVALENCE_UNPROVEN (see module docstring):
    # no live compilation or differential execution proof exists locally.
    return result.target_sql, TranslationCertification.COMPILES_BUT_EQUIVALENCE_UNPROVEN, findings


def make_sql_translation_producer(schema_model_resolver):
    """IntelligenceKernel-compatible producer for IntelligenceTask.CONVERT.
    request.parameters must contain 'target_engine'; optional 'target_version'.
    """

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        target_engine = request.parameters.get("target_engine")
        if not target_engine:
            raise IntelligenceValidationError("SQL translation requires request.parameters['target_engine'].")
        target_version = request.parameters.get("target_version")

        model = schema_model_resolver(request, context)
        package = DDLGenerator.generate_ddl_package(model, str(target_engine), target_version=target_version)

        certification = certify_package(package.artifacts)
        safety_counts = Counter(a.safety.value for a in package.artifacts)

        findings: List[DiagnosticFinding] = []
        for art in package.artifacts:
            if art.safety in (ConversionSafety.EXACT, ConversionSafety.SEMANTICALLY_EQUIVALENT):
                continue
            detail = "; ".join(art.warnings) if art.warnings else f"classified {art.safety.value} by the target DDL emitter"
            findings.append(
                DiagnosticFinding(
                    code=f"SQL_TRANSLATION:{art.safety.value}",
                    severity="HIGH" if art.safety in (ConversionSafety.LOSSY, ConversionSafety.UNSUPPORTED) else "MEDIUM",
                    message=f"{art.qualified_name} ({art.object_type}): {detail}",
                    evidence_refs=[art.qualified_name],
                )
            )

        # --- Procedural translation (routines: PROCEDURE/FUNCTION only) -------
        routines = list(getattr(model, "routines", ()) or ())
        translated_routine_sql = {}
        for routine in routines:
            emitted, routine_cert, routine_findings = _translate_routine(
                routine,
                source_vendor=getattr(model, "source_vendor", ""),
                target_engine=str(target_engine),
                schema_name=getattr(routine, "schema_name", "public"),
            )
            certification = _worse(certification, routine_cert)
            findings.extend(routine_findings)
            if emitted:
                translated_routine_sql[getattr(routine, "qualified_name", routine.name)] = emitted

        # Triggers/packages: no AST entrypoint exists in this repository for
        # either (verified by inspection) -- reported honestly, not attempted.
        unsupported_procedural_count = len(getattr(model, "triggers", ()) or ()) + len(getattr(model, "packages", ()) or ())
        if unsupported_procedural_count:
            certification = _worse(certification, TranslationCertification.UNSUPPORTED)
            findings.append(
                DiagnosticFinding(
                    code="SQL_TRANSLATION:UNSUPPORTED_IN_THIS_SCOPE",
                    severity="HIGH",
                    message=f"{unsupported_procedural_count} trigger/package object(s) have no procedural AST "
                    f"entrypoint in this repository -- reported, not silently dropped.",
                )
            )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=f"Translation to {target_engine!r}: {len(package.artifacts)} DDL statement(s), "
            f"{len(routines)} routine(s) processed, overall certification {certification.value}.",
            explanation=Explanation(
                summary="DDL certification aggregated from real per-statement ConversionSafety classifications; "
                "procedural certification from real PLSQLParser/TSQLParser -> PLpgSQLEmitter transpilation plus a "
                "local static soundness check -- overall certification is never better than the worst of either.",
                supporting_facts=[f"{k}={v}" for k, v in sorted(safety_counts.items())]
                + [f"routines_translated={len(translated_routine_sql)}/{len(routines)}"],
                contradictions=[] if certification != TranslationCertification.UNSUPPORTED else [
                    "At least one object has no valid target representation or supported translation path."
                ],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0,
                missing_information=(
                    ["live differential execution against a real target engine (EXTERNAL_DEFERRED)"]
                    + (["trigger/package translation (no AST entrypoint in this repository)"] if unsupported_procedural_count else [])
                ),
            ),
            findings=findings,
            data={
                "certification": certification.value,
                "target_engine": str(target_engine),
                "statement_count": len(package.artifacts),
                "safety_counts": dict(safety_counts),
                "ddl_sql": package.get_all_sql(),
                "routine_translation_sql": translated_routine_sql,
                "routines_total": len(routines),
                "routines_translated": len(translated_routine_sql),
            },
        )

    return producer
