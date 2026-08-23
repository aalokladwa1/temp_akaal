"""
akaalEngine.schema.ddl.providers.sqlite
=======================================
SQLite target DDL emitter for Authority #4 Schema.
Handles SQLite single-file schema semantics, dynamic affinity types, inline PK/FKs, and lack of separate user schemas.
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


class SQLiteDDLEmitter(BaseTargetDDLEmitter):
    """DDL emitter for SQLite 3 targets."""

    def __init__(self, target_engine: str = "SQLITE"):
        super().__init__(target_engine="SQLITE")

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        # SQLite does not support CREATE SCHEMA (uses attached databases)
        return []

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts: List[StructuredDDLArtifact] = []
        t_name = IdentifierSanitizer.sanitize_identifier(table.table_name, "SQLITE")

        col_defs = []
        for col in table.columns:
            c_name = IdentifierSanitizer.sanitize_identifier(col.name, "SQLITE")
            emission = ProviderTypeEmitters.emit_target_type(col.canonical_type, "SQLITE")
            col_sql = f"{c_name} {emission.target_native_type}"

            if not col.nullable:
                col_sql += " NOT NULL"
            if col.default_expression:
                col_sql += f" DEFAULT {col.default_expression}"
            if col.is_identity:
                col_sql += " PRIMARY KEY AUTOINCREMENT"
            col_defs.append(col_sql)

        # Primary Key (if not already inline AUTOINCREMENT)
        has_autoincrement = any(c.is_identity for c in table.columns)
        if table.primary_key and table.primary_key.columns and not has_autoincrement:
            pk_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "SQLITE") for c in table.primary_key.columns)
            col_defs.append(f"PRIMARY KEY ({pk_cols})")

        # Inline Foreign Keys in SQLite
        for fk in table.foreign_keys:
            fk_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "SQLITE") for c in fk.columns)
            ref_tbl = IdentifierSanitizer.sanitize_identifier(fk.referenced_table, "SQLITE")
            ref_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "SQLITE") for c in fk.referenced_columns)
            fk_clause = f"FOREIGN KEY ({fk_cols}) REFERENCES {ref_tbl} ({ref_cols})"
            if fk.on_delete != "NO ACTION":
                fk_clause += f" ON DELETE {fk.on_delete}"
            if fk.on_update != "NO ACTION":
                fk_clause += f" ON UPDATE {fk.on_update}"
            col_defs.append(fk_clause)

        # Unique constraints
        for uc in table.unique_constraints:
            uc_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "SQLITE") for c in uc.columns)
            col_defs.append(f"UNIQUE ({uc_cols})")

        # Check constraints
        for ck in table.check_constraints:
            col_defs.append(f"CHECK ({ck.check_clause})")

        body = ",\n  ".join(col_defs)
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {t_name} (\n  {body}\n)"

        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=table.table_name,
                schema_name=table.schema_name or "main",
                sql=create_table_sql,
                target_engine="SQLITE",
                stage=DDLStage.TABLES,
            )
        )

        # Indexes
        for idx in table.indexes:
            idx_name = IdentifierSanitizer.sanitize_identifier(idx.name, "SQLITE")
            idx_cols = ", ".join(IdentifierSanitizer.sanitize_identifier(c, "SQLITE") for c in idx.columns)
            unique_kw = "UNIQUE " if idx.is_unique else ""
            where_kw = f" WHERE {idx.predicate_expression}" if idx.predicate_expression else ""
            idx_sql = f"CREATE {unique_kw}INDEX IF NOT EXISTS {idx_name} ON {t_name} ({idx_cols}){where_kw}"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="INDEX",
                    object_name=idx.name,
                    schema_name=table.schema_name or "main",
                    sql=idx_sql,
                    target_engine="SQLITE",
                    stage=DDLStage.INDEXES,
                    dependencies=(table.qualified_name,),
                )
            )

        return artifacts

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        v_name = IdentifierSanitizer.sanitize_identifier(view.view_name, "SQLITE")
        query = view.view_definition or "SELECT 1"
        sql = f"CREATE VIEW IF NOT EXISTS {v_name} AS\n{query}"
        return [
            StructuredDDLArtifact(
                object_type="VIEW",
                object_name=view.view_name,
                schema_name=view.schema_name or "main",
                sql=sql,
                target_engine="SQLITE",
                stage=DDLStage.VIEWS,
            )
        ]

    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        # SQLite uses AUTOINCREMENT / sqlite_sequence table internally
        return []

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        # SQLite does not support custom UDTs
        return []
