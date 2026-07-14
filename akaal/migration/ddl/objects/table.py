from typing import Tuple, Dict, Any
from akaal.migration.models import ObjectType, OperationType, Table
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class TableTranslator(BaseObjectTranslator):
    """Translator for Table database objects."""
    SUPPORTED_OBJECTS = {ObjectType.TABLE}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: Table, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_table_name = f"{schema_prefix}{quoted_name}"
        
        sql = builder.build_create_table(full_table_name, ["id INT PRIMARY KEY"])
        rollback_sql = builder.build_drop_table(full_table_name, if_exists=capabilities.supports_if_exists)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Table, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_table_name = f"{schema_prefix}{quoted_name}"
        
        sql = builder.build_drop_table(full_table_name, if_exists=capabilities.supports_if_exists)
        rollback_sql = builder.build_create_table(full_table_name, ["id INT PRIMARY KEY"])
        
        warnings = (f"Destructive operation: dropping table {obj.name}",)
        return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=warnings)

    def translate_alter(self, obj: Table, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Table object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the table translator instance
ObjectTranslatorRegistry.register(ObjectType.TABLE, TableTranslator())
