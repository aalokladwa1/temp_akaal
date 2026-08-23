"""
akaalEngine.schema.ddl.providers.snowflake
==========================================
Target DDL emitter for Snowflake Cloud Data Warehouse.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from akaalEngine.schema.ddl.emitter import (
    BaseTargetDDLEmitter,
    DDLStage,
    StructuredDDLArtifact,
)
from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
from akaalEngine.schema.models.programmables import CanonicalSequence, CanonicalUDT
from akaalEngine.schema.models.schema import CanonicalView
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import ConversionSafety
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


class SnowflakeDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for Snowflake."""

    def __init__(self):
        super().__init__("SNOWFLAKE")

    def quote(self, name: str) -> str:
        return IdentifierSanitizer.quote_identifier(IdentifierSanitizer.sanitize_identifier(name, "SNOWFLAKE", force_uppercase=True), "SNOWFLAKE")

    def format_qualified_name(self, schema_name: Optional[str], object_name: str) -> str:
        return IdentifierSanitizer.format_qualified_name(schema_name, object_name, "SNOWFLAKE")

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        q_schema = self.quote(schema_name)
        sql = f"CREATE SCHEMA IF NOT EXISTS {q_schema};"
        return [
            StructuredDDLArtifact(
                object_type="SCHEMA",
                object_name=schema_name,
                schema_name=schema_name,
                sql=sql,
                target_engine="SNOWFLAKE",
                stage=DDLStage.SCHEMAS,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(sequence.schema_name, sequence.name)
        sql = f"CREATE SEQUENCE IF NOT EXISTS {qual} START WITH {sequence.start_value} INCREMENT BY {sequence.increment_by};"
        return [
            StructuredDDLArtifact(
                object_type="SEQUENCE",
                object_name=sequence.name,
                schema_name=sequence.schema_name,
                sql=sql,
                target_engine="SNOWFLAKE",
                stage=DDLStage.SEQUENCES,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        return []

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        emission = CanonicalTypeRegistry.emit_target_type("SNOWFLAKE", col.canonical_type)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        q_name = self.quote(col.name)
        col_sql = f"{q_name} {emission.target_native_type}"

        if not col.nullable:
            col_sql += " NOT NULL"

        if col.default_expression:
            col_sql += f" DEFAULT {col.default_expression}"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts: List[StructuredDDLArtifact] = []
        s_name = table.schema_name or "PUBLIC"
        t_name = table.table_name
        qual_tbl = self.format_qualified_name(s_name, t_name)

        col_defs = []
        overall_safety = ConversionSafety.EXACT
        tbl_warnings = []

        for col in sorted(table.columns, key=lambda x: x.ordinal_position):
            col_sql, safety, warns = self.emit_column_definition(col, source_engine)
            col_defs.append(f"    {col_sql}")
            if safety != ConversionSafety.EXACT and overall_safety == ConversionSafety.EXACT:
                overall_safety = safety
            tbl_warnings.extend(warns)

        # Primary Key (Snowflake supports inline PK constraint metadata)
        if table.primary_key and table.primary_key.columns:
            pk_cols = [self.quote(c) for c in table.primary_key.columns]
            col_defs.append(f"    CONSTRAINT PRIMARY KEY ({', '.join(pk_cols)})")

        # Cluster By Clause if partitioning / clustering specified
        cluster_clause = ""
        if table.partitioning.partition_columns:
            cl_cols = [self.quote(c) for c in table.partitioning.partition_columns]
            cluster_clause = f"\nCLUSTER BY ({', '.join(cl_cols)})"

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + f"\n){cluster_clause};"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="SNOWFLAKE",
                stage=DDLStage.TABLES,
                safety=overall_safety,
                warnings=tuple(tbl_warnings),
            )
        )

        return artifacts

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(view.schema_name, view.view_name)
        mat_str = "MATERIALIZED " if view.is_materialized else ""
        sql = f"CREATE OR REPLACE {mat_str}VIEW {qual} AS\n{view.definition_sql};"
        return [
            StructuredDDLArtifact(
                object_type="VIEW",
                object_name=view.view_name,
                schema_name=view.schema_name,
                sql=sql,
                target_engine="SNOWFLAKE",
                stage=DDLStage.VIEWS,
                dependencies=tuple(view.dependencies),
                safety=ConversionSafety.EXACT,
            )
        ]
