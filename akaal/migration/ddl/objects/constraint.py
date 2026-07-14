from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, Constraint
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class ConstraintTranslator(BaseObjectTranslator):
    """Translator for Constraint database objects."""
    SUPPORTED_OBJECTS = {ObjectType.CONSTRAINT}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: Constraint, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_constraint_name = quoter.quote(obj.name)
        c_type = getattr(obj, "constraint_type", "UNIQUE") or "UNIQUE"
        
        sql = builder.build_add_constraint(full_table_name, quoted_constraint_name, c_type)
        rollback_sql = builder.build_drop_constraint(full_table_name, quoted_constraint_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Constraint, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema = context.get("schema") or obj.schema
        schema_prefix = f"{quoter.quote(schema)}." if schema else ""
        parent_table = context.get("table_name", "unknown_table")
        full_table_name = f"{schema_prefix}{quoter.quote(parent_table)}"
        
        quoted_constraint_name = quoter.quote(obj.name)
        
        sql = builder.build_drop_constraint(full_table_name, quoted_constraint_name)
        rollback_sql = builder.build_add_constraint(full_table_name, quoted_constraint_name, "UNIQUE")
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: Constraint, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Constraint object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the constraint translator instance
ObjectTranslatorRegistry.register(ObjectType.CONSTRAINT, ConstraintTranslator())
