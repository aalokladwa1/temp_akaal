from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.core.models.enums import SystemType

class MaterializedViewTranslator(BaseObjectTranslator):
    """Dialect-aware translator for MaterializedView database objects."""
    SUPPORTED_OBJECTS = {ObjectType.MATERIALIZED_VIEW}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        target_dialect = context.get("target_dialect", SystemType.POSTGRESQL)
        tgt = target_dialect.value.lower() if hasattr(target_dialect, "value") else str(target_dialect).lower()

        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_mv_name = f"{schema_prefix}{quoted_name}"
        
        definition = getattr(obj, "definition", "SELECT 1") or "SELECT 1"
        refresh_mode = getattr(obj, "refresh_mode", "DEMAND") or "DEMAND"
        refresh_method = getattr(obj, "refresh_method", "FORCE") or "FORCE"

        # 1. Skip on MySQL
        if tgt in ("mysql", "mariadb", "sqlite"):
            warning = f"Target database dialect '{tgt}' does not support materialized views. Materialized view '{obj.name}' skipped."
            return TranslationResult(sql="", rollback_sql="", warnings=(warning,))

        # 2. Compile for PostgreSQL
        if tgt in ("postgresql", "postgres"):
            warnings = ()
            if refresh_mode.upper() == "COMMIT":
                warnings = ("PostgreSQL does not support COMMIT refresh mode for materialized views. Refresh must be triggered on-demand via REFRESH MATERIALIZED VIEW.",)
            sql = f"CREATE MATERIALIZED VIEW {full_mv_name} AS {definition}"
            rollback_sql = f"DROP MATERIALIZED VIEW {full_mv_name}"
            return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=warnings)

        # 3. Compile for Oracle
        if tgt == "oracle":
            sql = f"CREATE MATERIALIZED VIEW {full_mv_name} BUILD IMMEDIATE REFRESH {refresh_method} ON {refresh_mode} AS {definition}"
            rollback_sql = f"DROP MATERIALIZED VIEW {full_mv_name}"
            return TranslationResult(sql=sql, rollback_sql=rollback_sql)

        # 4. Compile for SQL Server (using indexed views)
        if tgt in ("mssql", "sqlserver"):
            warning = "SQL Server does not support native Materialized Views. Created indexed view template; a unique clustered index must be created to materialize it."
            sql = f"CREATE VIEW {full_mv_name} WITH SCHEMABINDING AS {definition}"
            rollback_sql = f"DROP VIEW {full_mv_name}"
            return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=(warning,))

        # Fallback default
        sql = f"CREATE MATERIALIZED VIEW {full_mv_name} AS {definition}"
        rollback_sql = f"DROP MATERIALIZED VIEW {full_mv_name}"
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        target_dialect = context.get("target_dialect", SystemType.POSTGRESQL)
        tgt = target_dialect.value.lower() if hasattr(target_dialect, "value") else str(target_dialect).lower()

        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_mv_name = f"{schema_prefix}{quoted_name}"

        if tgt in ("mysql", "mariadb", "sqlite"):
            return TranslationResult(sql="", rollback_sql="")

        if tgt in ("mssql", "sqlserver"):
            sql = f"DROP VIEW {full_mv_name}"
        else:
            sql = f"DROP MATERIALIZED VIEW {full_mv_name}"
            
        return TranslationResult(sql=sql, rollback_sql="")

    def translate_alter(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on MaterializedView object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the translator
ObjectTranslatorRegistry.register(ObjectType.MATERIALIZED_VIEW, MaterializedViewTranslator())
