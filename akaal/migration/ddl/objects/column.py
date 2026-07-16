from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, Column
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class ColumnTranslator(BaseObjectTranslator):
    """Translator for Column database objects."""
    SUPPORTED_OBJECTS = {ObjectType.COLUMN}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP, OperationType.ALTER}

    def translate_create(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_col_name = quoter.quote(obj.name)
        data_type = getattr(obj, "data_type", "VARCHAR(255)") or "VARCHAR(255)"
        
        identity_clause = ""
        if getattr(obj, "identity", None) is not None:
            from akaal.migration.ddl.objects.identity import IdentityTranslator
            ident_translator = IdentityTranslator()
            ident_res = ident_translator.translate_create(obj, context, quoter, capabilities, builder)
            if ident_res.sql:
                identity_clause = " " + ident_res.sql
        
        null_clause = " NOT NULL" if not obj.nullable else ""
        default_clause = f" DEFAULT {obj.default}" if obj.default else ""
        
        full_type_desc = f"{data_type}{identity_clause}{null_clause}{default_clause}"
        sql = builder.build_add_column(full_table_name, quoted_col_name, full_type_desc)
        rollback_sql = builder.build_drop_column(full_table_name, quoted_col_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_col_name = quoter.quote(obj.name)
        
        sql = builder.build_drop_column(full_table_name, quoted_col_name)
        rollback_sql = builder.build_add_column(full_table_name, quoted_col_name, "VARCHAR(255)")
        
        warnings = (f"Destructive operation: dropping column {obj.name} from {parent_table}",)
        return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=warnings)

    def translate_alter(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_col_name = quoter.quote(obj.name)
        
        sql = f"ALTER TABLE {full_table_name} ALTER COLUMN {quoted_col_name} TYPE VARCHAR(255)"
        rollback_sql = f"ALTER TABLE {full_table_name} ALTER COLUMN {quoted_col_name} TYPE VARCHAR(100)"
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

# Register the column translator instance
ObjectTranslatorRegistry.register(ObjectType.COLUMN, ColumnTranslator())
