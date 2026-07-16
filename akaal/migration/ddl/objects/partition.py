from typing import Dict, Any, Optional
from akaal.migration.models import ObjectType, OperationType, Partition, PartitionType
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class PartitionTranslator(BaseObjectTranslator):
    """
    Translates Range, List, and Hash partitioning commands for tables into vendor-specific SQL.
    Supports subpartition-ready structures and validation.
    """
    SUPPORTED_OBJECTS = {ObjectType.PARTITION}
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

    def translate_create(self, obj: Partition, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        dialect = self._get_dialect(quoter)
        sql = ""
        rollback_sql = ""
        warnings = []

        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_partition_name = f"{schema_prefix}{quoted_name}"
        
        parent_table = obj.table_name or context.get("table_name", "unknown_table")
        quoted_parent = quoter.quote(parent_table)
        full_parent_name = f"{schema_prefix}{quoted_parent}"

        p_type = obj.partition_type
        if isinstance(p_type, str):
            # Safe conversion if string was passed
            try:
                p_type = PartitionType(p_type)
            except ValueError:
                p_type = PartitionType.RANGE

        # Build boundaries description
        expression = obj.expression
        values_list = ", ".join(obj.values)

        if dialect == "postgresql":
            # PostgreSQL partitions are separate child tables
            if p_type == PartitionType.RANGE:
                # Expects 2 values for FROM and TO
                from_val = obj.values[0] if len(obj.values) > 0 else "MINVALUE"
                to_val = obj.values[1] if len(obj.values) > 1 else "MAXVALUE"
                sql = f"CREATE TABLE {full_partition_name} PARTITION OF {full_parent_name} FOR VALUES FROM ({from_val}) TO ({to_val})"
            elif p_type == PartitionType.LIST:
                sql = f"CREATE TABLE {full_partition_name} PARTITION OF {full_parent_name} FOR VALUES IN ({values_list})"
            elif p_type == PartitionType.HASH:
                # Expects modulus and remainder
                modulus = context.get("modulus", 1)
                remainder = context.get("remainder", 0)
                sql = f"CREATE TABLE {full_partition_name} PARTITION OF {full_parent_name} FOR VALUES WITH (MODULUS {modulus}, REMAINDER {remainder})"
            
            rollback_sql = f"DROP TABLE {full_partition_name}"

        elif dialect in ("mysql", "oracle"):
            # MySQL / Oracle partitions are added onto the table definition
            if p_type == PartitionType.RANGE:
                bound = obj.values[0] if obj.values else "MAXVALUE"
                sql = f"ALTER TABLE {full_parent_name} ADD PARTITION (PARTITION {quoted_name} VALUES LESS THAN ({bound}))"
            elif p_type == PartitionType.LIST:
                sql = f"ALTER TABLE {full_parent_name} ADD PARTITION (PARTITION {quoted_name} VALUES IN ({values_list}))"
            elif p_type == PartitionType.HASH:
                # Hash partitions are usually defined at table creation time, not added dynamically
                warnings.append("Hash partitioning must be declared at table creation time on MySQL/Oracle.")
                sql = ""

            rollback_sql = f"ALTER TABLE {full_parent_name} DROP PARTITION {quoted_name}"

        elif dialect == "mssql":
            # MSSQL partition alteration
            if p_type == PartitionType.RANGE:
                bound = obj.values[0] if obj.values else "0"
                sql = f"ALTER PARTITION FUNCTION {quoted_name}() SPLIT RANGE ({bound})"
                rollback_sql = f"ALTER PARTITION FUNCTION {quoted_name}() MERGE RANGE ({bound})"
            else:
                warnings.append("SQL Server only natively supports RANGE partitioning.")

        return TranslationResult(sql=sql, rollback_sql=rollback_sql, warnings=tuple(warnings))

    def translate_drop(self, obj: Partition, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        dialect = self._get_dialect(quoter)
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_partition_name = f"{schema_prefix}{quoted_name}"
        
        parent_table = obj.table_name or context.get("table_name", "unknown_table")
        quoted_parent = quoter.quote(parent_table)
        full_parent_name = f"{schema_prefix}{quoted_parent}"

        sql = ""
        rollback_sql = ""

        if dialect == "postgresql":
            sql = f"DROP TABLE {full_partition_name}"
        elif dialect in ("mysql", "oracle"):
            sql = f"ALTER TABLE {full_parent_name} DROP PARTITION {quoted_name}"
        elif dialect == "mssql":
            bound = obj.values[0] if obj.values else "0"
            sql = f"ALTER PARTITION FUNCTION {quoted_name}() MERGE RANGE ({bound})"

        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: Partition, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        return TranslationResult(sql="", rollback_sql="")

# Register/overwrite the partition translator
try:
    ObjectTranslatorRegistry.register(ObjectType.PARTITION, PartitionTranslator())
except ValueError:
    pass
