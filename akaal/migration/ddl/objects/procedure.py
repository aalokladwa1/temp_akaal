from typing import Dict, Any, Optional
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.core.conversion.api.service import IProcedureConversionService, ConversionRequest
from akaal.core.conversion.api.models import ConversionContext
from akaal.core.models.enums import SystemType

class ProcedureTranslator(BaseObjectTranslator):
    """DDL translator for Procedure database objects that delegates to ProcedureConversionService."""
    SUPPORTED_OBJECTS = {ObjectType.PROCEDURE}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def __init__(self, service: Optional[IProcedureConversionService] = None):
        super().__init__()
        self._service = service

    def set_service(self, service: IProcedureConversionService) -> None:
        self._service = service

    def translate_create(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        if not self._service:
            # Fallback mapping if not bootstrapped: generate a warning and standard placeholder
            schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
            quoted_name = quoter.quote(obj.name)
            full_proc_name = f"{schema_prefix}{quoted_name}"
            sql = f"CREATE PROCEDURE {full_proc_name}"
            rollback_sql = f"DROP PROCEDURE {full_proc_name}"
            return TranslationResult(
                sql=sql,
                rollback_sql=rollback_sql,
                warnings=("Procedure conversion service not initialized; using standard placeholder DDL.",)
            )

        source_dialect = context.get("source_dialect", SystemType.ORACLE)
        target_dialect = context.get("target_dialect", SystemType.POSTGRESQL)

        conv_context = ConversionContext(
            source_version=context.get("source_version", "19c"),
            target_version=context.get("target_version", "15"),
            connection_options=()
        )

        req = ConversionRequest(
            source_ddl=obj.definition,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            context=conv_context
        )

        try:
            res = self._service.convert_procedure(req)
            warnings = tuple(d.message for d in res.diagnostics)
            if not res.success:
                return TranslationResult(sql="", warnings=warnings)
            return TranslationResult(
                sql=res.target_sql,
                rollback_sql=res.rollback_plan.rollback_sql_template,
                warnings=warnings
            )
        except Exception as e:
            return TranslationResult(sql="", warnings=(f"Procedure conversion service error: {e}",))

    def translate_drop(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_proc_name = f"{schema_prefix}{quoted_name}"
        
        sql = f"DROP PROCEDURE IF EXISTS {full_proc_name}"
        return TranslationResult(sql=sql, rollback_sql="")

    def translate_alter(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Procedure object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the instance
procedure_translator = ProcedureTranslator()
ObjectTranslatorRegistry.register(ObjectType.PROCEDURE, procedure_translator)

