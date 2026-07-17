from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.core.models.enums import SystemType

class SynonymTranslator(BaseObjectTranslator):
    """Dialect-aware translator for Synonym database objects."""
    SUPPORTED_OBJECTS = {ObjectType.SYNONYM}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        target_dialect = context.get("target_dialect", SystemType.POSTGRESQL)
        tgt = target_dialect.value.lower() if hasattr(target_dialect, "value") else str(target_dialect).lower()

        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_synonym_name = f"{schema_prefix}{quoted_name}"
        
        target_object = getattr(obj, "object_name", "unknown_object")
        quoted_target = quoter.quote(target_object)

        # 1. Skip on unsupported databases
        if tgt in ("postgresql", "postgres", "mysql", "mariadb", "sqlite"):
            warning = f"Target database dialect '{tgt}' does not support synonyms natively. Synonym '{obj.name}' migration skipped."
            return TranslationResult(sql="", rollback_sql="", warnings=(warning,))

        # 2. Build for Oracle (supports PUBLIC synonyms)
        if tgt == "oracle":
            is_public = getattr(obj, "is_public", False)
            public_clause = " PUBLIC" if is_public else ""
            sql = f"CREATE{public_clause} SYNONYM {full_synonym_name} FOR {quoted_target}"
            rollback_sql = f"DROP{public_clause} SYNONYM {full_synonym_name}"
            return TranslationResult(sql=sql, rollback_sql=rollback_sql)

        # 3. Build for SQL Server (no public synonyms support)
        if tgt in ("mssql", "sqlserver"):
            warnings = ()
            if getattr(obj, "is_public", False):
                warnings = ("SQL Server does not support PUBLIC synonyms. Converting to standard schema synonym.",)
            sql = f"CREATE SYNONYM {full_synonym_name} FOR {quoted_target}"
            rollback_sql = f"DROP SYNONYM {full_synonym_name}"
            return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=warnings)

        # Fallback default
        sql = f"CREATE SYNONYM {full_synonym_name} FOR {quoted_target}"
        rollback_sql = f"DROP SYNONYM {full_synonym_name}"
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        target_dialect = context.get("target_dialect", SystemType.POSTGRESQL)
        tgt = target_dialect.value.lower() if hasattr(target_dialect, "value") else str(target_dialect).lower()

        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_synonym_name = f"{schema_prefix}{quoted_name}"

        if tgt in ("postgresql", "postgres", "mysql", "mariadb", "sqlite"):
            return TranslationResult(sql="", rollback_sql="")

        is_public = getattr(obj, "is_public", False)
        public_clause = " PUBLIC" if (is_public and tgt == "oracle") else ""
        sql = f"DROP{public_clause} SYNONYM {full_synonym_name}"
        return TranslationResult(sql=sql, rollback_sql="")

    def translate_alter(self, obj, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Synonym object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the translator
ObjectTranslatorRegistry.register(ObjectType.SYNONYM, SynonymTranslator())
