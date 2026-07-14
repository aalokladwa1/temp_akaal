from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, Trigger
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class TriggerTranslator(BaseObjectTranslator):
    """Translator for Trigger database objects."""
    SUPPORTED_OBJECTS = {ObjectType.TRIGGER}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: Trigger, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        
        quoted_trigger_name = quoter.quote(obj.name)
        parent_table = getattr(obj, "table_name", "unknown_table") or "unknown_table"
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        timing = getattr(obj, "timing", "BEFORE") or "BEFORE"
        event = getattr(obj, "event", "INSERT") or "INSERT"
        definition = getattr(obj, "definition", "FOR EACH ROW EXECUTE PROCEDURE test()") or "FOR EACH ROW EXECUTE PROCEDURE test()"
        
        sql = builder.build_create_trigger(quoted_trigger_name, full_table_name, timing, event, definition)
        rollback_sql = builder.build_drop_trigger(quoted_trigger_name, full_table_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Trigger, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        
        quoted_trigger_name = quoter.quote(obj.name)
        parent_table = getattr(obj, "table_name", "unknown_table") or "unknown_table"
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        sql = builder.build_drop_trigger(quoted_trigger_name, full_table_name)
        rollback_sql = builder.build_create_trigger(quoted_trigger_name, full_table_name, "BEFORE", "INSERT", "FOR EACH ROW EXECUTE PROCEDURE test()")
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: Trigger, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Trigger object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the trigger translator instance
ObjectTranslatorRegistry.register(ObjectType.TRIGGER, TriggerTranslator())
