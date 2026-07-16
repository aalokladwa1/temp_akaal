from typing import Tuple, Dict, Any
from akaal.migration.models import ObjectType, OperationType, Table
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class TableTranslator(BaseObjectTranslator):
    """Translator for Table database objects."""
    SUPPORTED_OBJECTS = {ObjectType.TABLE}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def _get_dialect(self, quoter) -> str:
        if quoter.quote_char_left == '`':
            return "mysql"
        elif quoter.quote_char_left == '[':
            return "mssql"
        elif quoter.quote_char_left == '"':
            if getattr(quoter, "force_upper", False):
                return "oracle"
            return "postgresql"
        return "postgresql"

    def translate_create(self, obj: Table, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_table_name = f"{schema_prefix}{quoted_name}"
        dialect = self._get_dialect(quoter)

        # Build column SQL definitions dynamically
        column_defs = []
        if not obj.columns:
            # Fallback for baseline support
            column_defs.append("id INT PRIMARY KEY")
        else:
            for col in obj.columns:
                col_name = quoter.quote(col.name)
                col_type = col.data_type or "VARCHAR(255)"
                
                identity_clause = ""
                if getattr(col, "identity", None) is not None:
                    from akaal.migration.ddl.objects.identity import IdentityTranslator
                    ident_translator = IdentityTranslator()
                    ident_res = ident_translator.translate_create(col, context, quoter, capabilities, builder)
                    if ident_res.sql:
                        identity_clause = " " + ident_res.sql

                null_clause = " NOT NULL" if not col.nullable else ""
                default_clause = f" DEFAULT {col.default}" if col.default else ""
                column_defs.append(f"{col_name} {col_type}{identity_clause}{null_clause}{default_clause}")

        # Add constraints
        for c in obj.constraints:
            c_name = quoter.quote(c.name)
            cols = ", ".join(quoter.quote(x) for x in c.columns)
            if c.constraint_type == "PRIMARY KEY":
                column_defs.append(f"CONSTRAINT {c_name} PRIMARY KEY ({cols})")
            elif c.constraint_type == "UNIQUE":
                column_defs.append(f"CONSTRAINT {c_name} UNIQUE ({cols})")

        sql = builder.build_create_table(full_table_name, column_defs)

        # Append Table-level partitioning clauses
        if obj.partition_metadata is not None:
            pm = obj.partition_metadata
            keys = ", ".join(quoter.quote(k) for k in pm.partition_keys)
            partition_clause = f" PARTITION BY {pm.partition_type.value} ({keys})"

            if dialect in ("mysql", "oracle") and pm.boundaries:
                bounds_sql = []
                for part_name, bound in pm.boundaries.items():
                    quoted_part = quoter.quote(part_name)
                    if bound.less_than:
                        bounds_sql.append(f"PARTITION {quoted_part} VALUES LESS THAN ({bound.less_than})")
                    elif bound.in_values:
                        vals = ", ".join(bound.in_values)
                        bounds_sql.append(f"PARTITION {quoted_part} VALUES IN ({vals})")
                if bounds_sql:
                    partition_clause += f" ({', '.join(bounds_sql)})"
            
            sql += partition_clause

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
