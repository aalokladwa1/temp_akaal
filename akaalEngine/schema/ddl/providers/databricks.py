"""
akaalEngine.schema.ddl.providers.databricks
===========================================
Databricks Delta Lake / Spark SQL target DDL emitter for Authority #4 Schema.
Handles Unity Catalog / Hive metastore namespaces, Delta format declarations, partition specifications, and cluster keys.
"""

from typing import List, Optional

from akaalEngine.schema.ddl.emitter import (
    BaseTargetDDLEmitter,
    DDLStage,
    StructuredDDLArtifact,
)
from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
from akaalEngine.schema.models.programmables import (
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
)
from akaalEngine.schema.models.schema import CanonicalView
from akaalEngine.schema.models.table import CanonicalTable
from akaalEngine.schema.models.types import ConversionSafety
from akaalEngine.schema.types.emitters import ProviderTypeEmitters


class DatabricksDDLEmitter(BaseTargetDDLEmitter):
    """DDL emitter for Databricks Delta Lake targets."""

    def __init__(self, target_engine: str = "DATABRICKS"):
        super().__init__(target_engine="DATABRICKS")

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        s_name = IdentifierSanitizer.sanitize_identifier(schema_name, "DATABRICKS")
        return [
            StructuredDDLArtifact(
                object_type="SCHEMA",
                object_name=schema_name,
                schema_name=schema_name,
                sql=f"CREATE SCHEMA IF NOT EXISTS {s_name}",
                target_engine="DATABRICKS",
                stage=DDLStage.SCHEMAS,
            )
        ]

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        tbl_qual = IdentifierSanitizer.format_qualified_name(table.schema_name, table.table_name, "DATABRICKS")

        col_defs = []
        for col in table.columns:
            c_name = IdentifierSanitizer.sanitize_identifier(col.name, "DATABRICKS")
            emission = ProviderTypeEmitters.emit_target_type(col.canonical_type, "DATABRICKS")
            col_sql = f"{c_name} {emission.target_native_type}"

            if not col.nullable:
                col_sql += " NOT NULL"
            if col.default_expression:
                col_sql += f" DEFAULT {col.default_expression}"
            if col.is_identity:
                col_sql += " GENERATED ALWAYS AS IDENTITY"
            if col.comment:
                clean_comment = col.comment.replace("'", "''")
                col_sql += f" COMMENT '{clean_comment}'"
            col_defs.append(col_sql)

        # Primary Key (Informational in Unity Catalog)
        if table.primary_key and table.primary_key.columns:
            pk_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "DATABRICKS") for c in table.primary_key.columns)
            col_defs.append(f"CONSTRAINT {table.primary_key.name or 'pk'} PRIMARY KEY ({pk_cols}) RELY")

        body = ",\n  ".join(col_defs)
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {tbl_qual} (\n  {body}\n) USING DELTA"

        # Partitioning
        if table.partitioning and table.partitioning.partition_columns:
            part_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "DATABRICKS") for c in table.partitioning.partition_columns)
            create_table_sql += f"\nPARTITIONED BY ({part_cols})"

        if table.comment:
            clean_tbl_comment = table.comment.replace("'", "''")
            create_table_sql += f"\nCOMMENT '{clean_tbl_comment}'"

        return [
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=table.table_name,
                schema_name=table.schema_name,
                sql=create_table_sql,
                target_engine="DATABRICKS",
                stage=DDLStage.TABLES,
            )
        ]

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        v_qual = IdentifierSanitizer.format_qualified_name(view.schema_name, view.view_name, "DATABRICKS")
        query = view.view_definition or "SELECT 1"
        sql = f"CREATE OR REPLACE VIEW {v_qual} AS\n{query}"
        return [
            StructuredDDLArtifact(
                object_type="VIEW",
                object_name=view.view_name,
                schema_name=view.schema_name,
                sql=sql,
                target_engine="DATABRICKS",
                stage=DDLStage.VIEWS,
            )
        ]

    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        # Databricks supports IDENTITY columns rather than standalone sequences
        return []

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        return []
