from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, View
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class ViewTranslator(BaseObjectTranslator):
    """Translator for View database objects."""
    SUPPORTED_OBJECTS = {ObjectType.VIEW}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: View, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_view_name = f"{schema_prefix}{quoted_name}"
        
        definition = getattr(obj, "definition", "SELECT 1") or "SELECT 1"
        sql = builder.build_create_view(full_view_name, definition)
        rollback_sql = builder.build_drop_view(full_view_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: View, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_view_name = f"{schema_prefix}{quoted_name}"
        
        sql = builder.build_drop_view(full_view_name)
        rollback_sql = builder.build_create_view(full_view_name, "SELECT 1")
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: View, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on View object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the view translator instance
ObjectTranslatorRegistry.register(ObjectType.VIEW, ViewTranslator())
