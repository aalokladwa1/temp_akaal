from typing import Dict, Any, Optional
from akaal.migration.models import ObjectType, OperationType, Column
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class IdentityTranslator(BaseObjectTranslator):
    """
    Translates identity column parameters (start, increment, generated always vs default,
    caching, cycle, min/max values) into vendor-specific SQL clauses.
    """
    SUPPORTED_OBJECTS = {ObjectType.COLUMN}  # Identity is part of COLUMN definition
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

    def translate_create(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        if not obj.identity:
            return TranslationResult(sql="", rollback_sql="")

        ident = obj.identity
        dialect = self._get_dialect(quoter)
        sql = ""
        warnings = []

        if dialect == "postgresql":
            gen_type = "ALWAYS" if ident.always else "BY DEFAULT"
            seq_options = []
            if ident.start != 1:
                seq_options.append(f"START WITH {ident.start}")
            if ident.increment != 1:
                seq_options.append(f"INCREMENT BY {ident.increment}")
            if ident.min_value is not None:
                seq_options.append(f"MINVALUE {ident.min_value}")
            if ident.max_value is not None:
                seq_options.append(f"MAXVALUE {ident.max_value}")
            if ident.cycle:
                seq_options.append("CYCLE")
            if ident.cache_size is not None:
                seq_options.append(f"CACHE {ident.cache_size}")

            seq_str = f" ({' '.join(seq_options)})" if seq_options else ""
            sql = f"GENERATED {gen_type} AS IDENTITY{seq_str}"

        elif dialect == "oracle":
            gen_type = "ALWAYS" if ident.always else "BY DEFAULT ON NULL"
            seq_options = []
            if ident.start != 1:
                seq_options.append(f"START WITH {ident.start}")
            if ident.increment != 1:
                seq_options.append(f"INCREMENT BY {ident.increment}")
            if ident.min_value is not None:
                seq_options.append(f"MINVALUE {ident.min_value}")
            if ident.max_value is not None:
                seq_options.append(f"MAXVALUE {ident.max_value}")
            if ident.cycle:
                seq_options.append("CYCLE")
            if ident.cache_size is not None:
                seq_options.append(f"CACHE {ident.cache_size}")

            seq_str = f" ({' '.join(seq_options)})" if seq_options else ""
            sql = f"GENERATED {gen_type} AS IDENTITY{seq_str}"

        elif dialect == "mssql":
            sql = f"IDENTITY({ident.start},{ident.increment})"
            if ident.cycle:
                warnings.append("SQL Server identity columns do not support CYCLE parameter.")

        elif dialect == "mysql":
            sql = "AUTO_INCREMENT"
            if ident.start != 1:
                # mysql starting value is table-level, warn or pass value in metadata
                pass

        return TranslationResult(sql=sql, rollback_sql="", warnings=tuple(warnings))

    def translate_drop(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        # Dropping identity metadata is resolved by altering the column
        dialect = self._get_dialect(quoter)
        sql = ""
        if dialect == "postgresql":
            sql = "DROP IDENTITY IF EXISTS"
        elif dialect == "oracle":
            sql = "DROP IDENTITY"
        return TranslationResult(sql=sql, rollback_sql="")

    def translate_alter(self, obj: Column, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        return TranslationResult(sql="", rollback_sql="")

# Helper class, invoked directly by Column/Table translators.
