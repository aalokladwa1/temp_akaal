from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, Index
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class IndexTranslator(BaseObjectTranslator):
    """Translator for Index database objects."""
    SUPPORTED_OBJECTS = {ObjectType.INDEX}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: Index, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_index_name = quoter.quote(obj.name)
        
        sql = builder.build_create_index(quoted_index_name, full_table_name, ["id"], unique=obj.unique)
        
        # Build rollback SQL using dialect capabilities
        drop_table_arg = full_table_name if capabilities.requires_index_table_on_drop else None
        rollback_sql = builder.build_drop_index(quoted_index_name, drop_table_arg)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Index, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_index_name = quoter.quote(obj.name)
        
        drop_table_arg = full_table_name if capabilities.requires_index_table_on_drop else None
        sql = builder.build_drop_index(quoted_index_name, drop_table_arg)
        rollback_sql = builder.build_create_index(quoted_index_name, full_table_name, ["id"], unique=obj.unique)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: Index, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Index object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the index translator instance
ObjectTranslatorRegistry.register(ObjectType.INDEX, IndexTranslator())
