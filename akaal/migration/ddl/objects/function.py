from typing import Dict, Any, Optional
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.core.conversion.api.service import IProcedureConversionService, ConversionRequest
from akaal.core.conversion.api.models import ConversionContext
from akaal.core.models.enums import SystemType

class FunctionTranslator(BaseObjectTranslator):
    """DDL translator for Function database objects that delegates to RoutineConversionService."""
    SUPPORTED_OBJECTS = {ObjectType.FUNCTION}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def __init__(self, service: Optional[Any] = None):
        super().__init__()
        self._service = service

    def set_service(self, service: Any) -> None:
        self._service = service

    def translate_create(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        if not self._service:
            # Fallback mapping: generate warning and standard placeholder
            schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
            quoted_name = quoter.quote(obj.name)
            full_func_name = f"{schema_prefix}{quoted_name}"
            sql = f"CREATE FUNCTION {full_func_name}"
            rollback_sql = f"DROP FUNCTION {full_func_name}"
            return TranslationResult(
                sql=sql,
                rollback_sql=rollback_sql,
                warnings=("Routine conversion service not initialized; using standard placeholder DDL.",)
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
            res = self._service.convert_function(req)
            warnings = tuple(d.message for d in res.diagnostics)
            if not res.success:
                return TranslationResult(sql="", warnings=warnings)
            return TranslationResult(
                sql=res.target_sql,
                rollback_sql=res.rollback_plan.rollback_sql_template,
                warnings=warnings
            )
        except Exception as e:
            return TranslationResult(sql="", warnings=(f"Function conversion service error: {e}",))

    def translate_drop(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_func_name = f"{schema_prefix}{quoted_name}"
        
        sql = f"DROP FUNCTION IF EXISTS {full_func_name}"
        return TranslationResult(sql=sql, rollback_sql="")

    def translate_alter(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Function object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the instance
function_translator = FunctionTranslator()
ObjectTranslatorRegistry.register(ObjectType.FUNCTION, function_translator)
