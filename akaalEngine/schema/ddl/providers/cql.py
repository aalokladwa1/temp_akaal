"""
akaalEngine.schema.ddl.providers.cql
====================================
Target DDL emitter for Apache Cassandra and ScyllaDB (CQL).
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


class CQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for Cassandra / ScyllaDB (CQL)."""

    def __init__(self, target_engine: str = "CASSANDRA"):
        super().__init__(target_engine)

    def quote(self, name: str) -> str:
        return IdentifierSanitizer.quote_identifier(IdentifierSanitizer.sanitize_identifier(name, self.target_engine, force_lowercase=True), self.target_engine)

    def format_qualified_name(self, schema_name: Optional[str], object_name: str) -> str:
        return IdentifierSanitizer.format_qualified_name(schema_name, object_name, self.target_engine)

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        q_keyspace = self.quote(schema_name)
        sql = f"CREATE KEYSPACE IF NOT EXISTS {q_keyspace} WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};"
        return [
            StructuredDDLArtifact(
                object_type="SCHEMA",
                object_name=schema_name,
                schema_name=schema_name,
                sql=sql,
                target_engine=self.target_engine,
                stage=DDLStage.SCHEMAS,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        return []

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(udt.schema_name, udt.name)
        if udt.attributes:
            attr_defs = []
            for attr_name, attr_type in udt.attributes.items():
                attr_defs.append(f"    {self.quote(attr_name)} {attr_type}")
            sql = f"CREATE TYPE IF NOT EXISTS {qual} (\n" + ",\n".join(attr_defs) + "\n);"
            return [
                StructuredDDLArtifact(
                    object_type="UDT",
                    object_name=udt.name,
                    schema_name=udt.schema_name,
                    sql=sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.TYPES,
                    safety=ConversionSafety.EXACT,
                )
            ]
        return []

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        emission = CanonicalTypeRegistry.emit_target_type("CASSANDRA", col.canonical_type)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        q_name = self.quote(col.name)
        col_sql = f"{q_name} {emission.target_native_type}"
        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts: List[StructuredDDLArtifact] = []
        s_name = table.schema_name or "system_data"
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

        # Primary Key (Partition Key + Clustering Columns)
        if table.primary_key and table.primary_key.columns:
            pk_cols = [self.quote(c) for c in table.primary_key.columns]
            col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + "\n);"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine=self.target_engine,
                stage=DDLStage.TABLES,
                safety=overall_safety,
                warnings=tuple(tbl_warnings),
            )
        )

        return artifacts

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(view.schema_name, view.view_name)
        if view.is_materialized and view.dependencies:
            sql = f"CREATE MATERIALIZED VIEW IF NOT EXISTS {qual} AS\n{view.definition_sql};"
            return [
                StructuredDDLArtifact(
                    object_type="MATERIALIZED_VIEW",
                    object_name=view.view_name,
                    schema_name=view.schema_name,
                    sql=sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.VIEWS,
                    dependencies=tuple(view.dependencies),
                    safety=ConversionSafety.EXACT,
                )
            ]
        return []
