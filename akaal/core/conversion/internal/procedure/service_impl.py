"""
Akaal — Stored Procedure Conversion Service Implementation
===========================================================
Implements the public IProcedureConversionService contract. Orchestrates the
parsing, semantic analysis, planning, and rendering stages.
"""

from typing import Tuple, List, Optional
import hashlib
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import (
    IProcedureConversionService,
    ConversionRequest,
    ConversionResponse,
    ObjectCompatibilityReport,
    ObjectCompatibilityTier,
    ConfidenceDimension,
    ConfidenceEvidence,
    CertificationDisposition,
    ManualReviewReason,
    RoutineRollbackPlan,
    RollbackActionKind
)
from akaal.core.conversion.api.aoir import TransactionBehavior
from akaal.core.conversion.api.diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
    DiagnosticCategory,
    StructuredRecommendation,
    RecommendationCategory
)
from akaal.core.conversion.internal.procedure.parser import ProcedureParser
from akaal.core.conversion.internal.procedure.renderer import PgSqlRenderer
from akaal.core.conversion.internal.analyzer import TransactionAnalyzer, DependencyAnalyzer

class ProcedureConversionService(IProcedureConversionService):
    def convert_procedure(self, request: ConversionRequest) -> ConversionResponse:
        # Validate vendor directions
        if request.source_dialect != SystemType.ORACLE or request.target_dialect != SystemType.POSTGRESQL:
            diag = Diagnostic(
                code="UNSUPPORTED_VENDOR_DIRECTION",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.COMPATIBILITY,
                message=f"Conversion direction from {request.source_dialect} to {request.target_dialect} is deferred or unsupported."
            )
            report = ObjectCompatibilityReport(
                target_object_name="UNKNOWN",
                compatibility_tier=ObjectCompatibilityTier.UNSUPPORTED,
                dimensions=(),
                disposition=CertificationDisposition.BLOCKED,
                manual_review_reasons=()
            )
            rollback = RoutineRollbackPlan(
                action_type=RollbackActionKind.UNSAFE_ABORT,
                target_object_name="UNKNOWN",
                rollback_sql_template=""
            )
            return ConversionResponse(
                target_sql="",
                rollback_plan=rollback,
                compatibility_report=report,
                success=False,
                diagnostics=(diag,)
            )

        diagnostics: List[Diagnostic] = []
        success = True

        try:
            # Stage 1: Parse Source
            parser = ProcedureParser(request.source_ddl)
            aoir = parser.parse_routine()
        except Exception as e:
            diag = Diagnostic(
                code="PARSE_FAILURE",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.ENGINE,
                message=f"Parser failed to tokenize or construct AST: {e}"
            )
            report = ObjectCompatibilityReport(
                target_object_name="UNKNOWN",
                compatibility_tier=ObjectCompatibilityTier.UNSUPPORTED,
                dimensions=(
                    ConfidenceEvidence(ConfidenceDimension.PARSER, 0.0, ("Parsing encountered fatal exception",)),
                ),
                disposition=CertificationDisposition.BLOCKED,
                manual_review_reasons=()
            )
            rollback = RoutineRollbackPlan(
                action_type=RollbackActionKind.UNSAFE_ABORT,
                target_object_name="UNKNOWN",
                rollback_sql_template=""
            )
            return ConversionResponse(
                target_sql="",
                rollback_plan=rollback,
                compatibility_report=report,
                success=False,
                diagnostics=(diag,)
            )

        # Log parser warning recoveries if any
        for warning in parser.diagnostics_log:
            diagnostics.append(Diagnostic(
                code="PARSER_RECOVERY_WARNING",
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.ENGINE,
                message=f"Parser recovered: {warning}"
            ))

        # Stage 2: Semantic & Transaction Analysis
        tx_analyzer = TransactionAnalyzer(parser.all_tokens, request.source_ddl)
        tx_behavior, unsupported_tx, review_reqs = tx_analyzer.analyze()

        # Check for autonomous transactions or dynamic SQL
        for unsup in unsupported_tx:
            diagnostics.append(Diagnostic(
                code=f"UNSUPPORTED_{unsup.construct_type}",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.COMPATIBILITY,
                message=unsup.description,
                related_object=aoir.name
            ))
            success = False

        manual_review_reasons = []
        for rev in review_reqs:
            diagnostics.append(Diagnostic(
                code=rev.reason_code,
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.POLICY,
                message=rev.description,
                related_object=aoir.name,
                remediation=StructuredRecommendation(
                    category=RecommendationCategory.MANUAL_ACTION,
                    severity=DiagnosticSeverity.WARNING,
                    description="Resolve lock boundaries or savepoint isolation manually in target database."
                )
            ))
            if rev.reason_code == "SAVEPOINT_DETECTED":
                manual_review_reasons.append(ManualReviewReason.COMPLEX_TRANSACTION_BLOCK)
            elif rev.reason_code == "DBMS_LOCK_DETECTED":
                manual_review_reasons.append(ManualReviewReason.UNSAFE_MUTATION_PATTERN)

        # Stage 3: Dependency Graph Sorting & Cycle Analysis
        dep_map = {aoir.name: list(aoir.dependencies)}
        dep_analyzer = DependencyAnalyzer(dep_map)
        sccs = dep_analyzer.find_sccs()
        cycle_results = dep_analyzer.classify_cycles(sccs)
        
        has_blocked_cycles = False
        for cycle in cycle_results:
            severity = DiagnosticSeverity.WARNING
            if cycle.resolution == "BLOCKED" or cycle.resolution == "UNRESOLVED_EXTERNAL":
                severity = DiagnosticSeverity.ERROR
                success = False
                has_blocked_cycles = True
            
            diagnostics.append(Diagnostic(
                code="DEPENDENCY_CYCLE_DETECTED",
                severity=severity,
                category=DiagnosticCategory.COMPATIBILITY,
                message=cycle.description,
                related_object=aoir.name
            ))
            if cycle.resolution == "UNRESOLVED_EXTERNAL":
                manual_review_reasons.append(ManualReviewReason.UNRESOLVED_DEPENDENCY)

        # Stage 4: Target Rendering
        target_sql = ""
        if success:
            try:
                renderer = PgSqlRenderer(aoir)
                target_sql = renderer.render()
            except Exception as e:
                diagnostics.append(Diagnostic(
                    code="RENDER_FAILURE",
                    severity=DiagnosticSeverity.ERROR,
                    category=DiagnosticCategory.ENGINE,
                    message=f"Renderer failed to compile target PL/pgSQL: {e}"
                ))
                success = False

        # Calculate Confidence Scores
        parser_score = 1.0 - (len(parser.diagnostics_log) * 0.1)
        parser_score = max(0.0, min(1.0, parser_score))

        semantic_score = 1.0
        if tx_behavior == TransactionBehavior.REQUIRES_MANUAL_REWRITE:
            semantic_score = 0.5
        elif tx_behavior == TransactionBehavior.REQUIRES_AUTONOMOUS_TRANSACTION_PROVIDER:
            semantic_score = 0.2

        dep_score = 0.5 if cycle_results else 1.0
        renderer_score = 1.0 if success else 0.0
        validation_score = 1.0 if success else 0.0

        dimensions = (
            ConfidenceEvidence(ConfidenceDimension.PARSER, parser_score, ("AST built cleanly",)),
            ConfidenceEvidence(ConfidenceDimension.SEMANTIC, semantic_score, (f"Transaction behavior classified: {tx_behavior.value}",)),
            ConfidenceEvidence(ConfidenceDimension.DEPENDENCY, dep_score, (f"Cycles processed: {len(cycle_results)}",)),
            ConfidenceEvidence(ConfidenceDimension.RENDERER, renderer_score, ("Rendering complete",) if success else ("Rendering failed",)),
            ConfidenceEvidence(ConfidenceDimension.VALIDATION, validation_score, ("Ready for Dry-Run",) if success else ("Compilation blocked",))
        )

        tier = ObjectCompatibilityTier.NATIVE
        disposition = CertificationDisposition.CERTIFIED

        if not success:
            tier = ObjectCompatibilityTier.UNSUPPORTED
            disposition = CertificationDisposition.BLOCKED
        elif manual_review_reasons:
            tier = ObjectCompatibilityTier.MANUAL_REVIEW
            disposition = CertificationDisposition.REQUIRES_MANUAL_SIGN_OFF

        report = ObjectCompatibilityReport(
            target_object_name=aoir.name,
            compatibility_tier=tier,
            dimensions=dimensions,
            disposition=disposition,
            manual_review_reasons=tuple(set(manual_review_reasons))
        )

        # Rollback plan generation
        h = hashlib.sha256(request.source_ddl.encode("utf-8")).hexdigest()
        rollback = RoutineRollbackPlan(
            action_type=RollbackActionKind.DROP_PROCEDURE,
            target_object_name=aoir.name,
            rollback_sql_template=f"DROP PROCEDURE IF EXISTS {aoir.name};",
            pre_migration_definition_hash=h
        )

        return ConversionResponse(
            target_sql=target_sql,
            rollback_plan=rollback,
            compatibility_report=report,
            success=success,
            diagnostics=tuple(diagnostics)
        )
