from typing import Tuple, List, Optional
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
    RoutineRollbackPlan,
    RollbackActionKind
)
from akaal.core.conversion.api.diagnostics import Diagnostic, DiagnosticSeverity, DiagnosticCategory
from akaal.core.conversion.internal.parser.routine_parser import RoutineParser
from akaal.core.conversion.internal.renderer.postgresql import PostgreSQLRoutineRenderer
from akaal.core.conversion.internal.renderer.oracle import OracleRoutineRenderer
from akaal.core.conversion.internal.renderer.mysql import MySQLRoutineRenderer
from akaal.core.conversion.internal.renderer.sqlserver import SQLServerRoutineRenderer

class RoutineConversionService(IProcedureConversionService):
    def convert_routine(self, request: ConversionRequest) -> ConversionResponse:
        # Check source and target dialects
        src_dialect = request.source_dialect.value.lower() if hasattr(request.source_dialect, "value") else str(request.source_dialect)
        tgt_dialect = request.target_dialect.value.lower() if hasattr(request.target_dialect, "value") else str(request.target_dialect)

        # Parse source routine into versioned AOIR
        try:
            parser = RoutineParser(request.source_ddl, source_dialect=src_dialect, target_dialect=tgt_dialect)
            aoir = parser.parse_routine()
        except Exception as e:
            diag = Diagnostic(
                code="PARSE_FAILURE",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.ENGINE,
                message=f"Parser failed to compile routine: {e}"
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

        # Select target renderer
        if tgt_dialect == "postgresql" or tgt_dialect == "postgres":
            renderer = PostgreSQLRoutineRenderer(aoir)
        elif tgt_dialect == "mysql":
            renderer = MySQLRoutineRenderer(aoir)
        elif tgt_dialect == "oracle":
            renderer = OracleRoutineRenderer(aoir)
        elif tgt_dialect == "sqlserver" or tgt_dialect == "mssql":
            renderer = SQLServerRoutineRenderer(aoir)
        else:
            raise ValueError(f"Unsupported target dialect: {tgt_dialect}")

        target_sql = renderer.render()

        report = ObjectCompatibilityReport(
            target_object_name=aoir.name,
            compatibility_tier=ObjectCompatibilityTier.NATIVE,
            dimensions=(),
            disposition=CertificationDisposition.CERTIFIED,
            manual_review_reasons=()
        )
        
        drop_type = "FUNCTION" if aoir.kind.value == "FUNCTION" else "PROCEDURE"
        rollback = RoutineRollbackPlan(
            action_type=RollbackActionKind.DROP_PROCEDURE,
            target_object_name=aoir.name,
            rollback_sql_template=f"DROP {drop_type} IF EXISTS {aoir.name}"
        )
        return ConversionResponse(
            target_sql=target_sql,
            rollback_plan=rollback,
            compatibility_report=report,
            success=True,
            diagnostics=()
        )

    def convert_procedure(self, request: ConversionRequest) -> ConversionResponse:
        return self.convert_routine(request)

    def convert_function(self, request: ConversionRequest) -> ConversionResponse:
        return self.convert_routine(request)
