"""
akaalEngine.schema.ddl.providers.mysql
======================================
Target DDL emitter for MySQL and MariaDB.
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


class MySQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for MySQL and MariaDB."""

    def __init__(self, target_engine: str = "MYSQL"):
        super().__init__(target_engine)

    def quote(self, name: str) -> str:
        return IdentifierSanitizer.quote_identifier(IdentifierSanitizer.sanitize_identifier(name, self.target_engine), self.target_engine)

    def format_qualified_name(self, schema_name: Optional[str], object_name: str) -> str:
        return IdentifierSanitizer.format_qualified_name(schema_name, object_name, self.target_engine)

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        q_schema = self.quote(schema_name)
        sql = f"CREATE DATABASE IF NOT EXISTS {q_schema};"
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
        if self.target_engine == "MARIADB":
            qual = self.format_qualified_name(sequence.schema_name, sequence.name)
            sql = f"CREATE SEQUENCE IF NOT EXISTS {qual} START WITH {sequence.start_value} INCREMENT BY {sequence.increment_by};"
            return [
                StructuredDDLArtifact(
                    object_type="SEQUENCE",
                    object_name=sequence.name,
                    schema_name=sequence.schema_name,
                    sql=sql,
                    target_engine=self.target_engine,
                    stage=DDLStage.SEQUENCES,
                    safety=ConversionSafety.EXACT,
                )
            ]
        # Standard MySQL does not have standalone SEQUENCE statements (uses AUTO_INCREMENT)
        return []

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        # MySQL does not support standalone CREATE TYPE; enums are inline
        return []

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        emission = CanonicalTypeRegistry.emit_target_type(self.target_engine, col.canonical_type)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        q_name = self.quote(col.name)
        col_sql = f"{q_name} {emission.target_native_type}"

        if not col.nullable and not col.is_identity:
            col_sql += " NOT NULL"

        if col.is_identity:
            col_sql += " AUTO_INCREMENT"

        if col.default_expression and not col.is_identity:
            col_sql += f" DEFAULT {col.default_expression}"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts: List[StructuredDDLArtifact] = []
        s_name = table.schema_name or "public"
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

        # Primary Key
        if table.primary_key and table.primary_key.columns:
            pk_cols = [self.quote(c) for c in table.primary_key.columns]
            col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")

        # Unique Constraints
        for uc in table.unique_constraints:
            if uc.columns:
                uc_cols = [self.quote(c) for c in uc.columns]
                uc_name = self.quote(uc.name) if uc.name else ""
                col_defs.append(f"    UNIQUE KEY {uc_name} ({', '.join(uc_cols)})")

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
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

        # Indexes
        for idx in table.indexes:
            if idx.columns:
                q_idx = self.quote(idx.name)
                unique_str = "UNIQUE " if idx.is_unique else ""
                cols_str = ", ".join([self.quote(c) for c in idx.columns])
                idx_sql = f"CREATE {unique_str}INDEX {q_idx} ON {qual_tbl} ({cols_str});"
                artifacts.append(
                    StructuredDDLArtifact(
                        object_type="INDEX",
                        object_name=idx.name,
                        schema_name=s_name,
                        sql=idx_sql,
                        target_engine=self.target_engine,
                        stage=DDLStage.INDEXES,
                        dependencies=(f"{s_name}.{t_name}",),
                        safety=ConversionSafety.EXACT,
                    )
                )

        # Foreign Keys
        for fk in table.foreign_keys:
            if fk.columns and fk.referenced_columns:
                fk_name = fk.name or f"fk_{t_name}_{'_'.join(fk.columns)}"
                q_fk = self.quote(fk_name)
                cols = ", ".join([self.quote(c) for c in fk.columns])
                ref_tbl = self.format_qualified_name(fk.referenced_schema, fk.referenced_table)
                ref_cols = ", ".join([self.quote(c) for c in fk.referenced_columns])
                actions = f" ON UPDATE {fk.on_update} ON DELETE {fk.on_delete}"
                fk_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {q_fk} FOREIGN KEY ({cols}) REFERENCES {ref_tbl} ({ref_cols}){actions};"
                ref_dep = f"{fk.referenced_schema}.{fk.referenced_table}"

                artifacts.append(
                    StructuredDDLArtifact(
                        object_type="FOREIGN_KEY",
                        object_name=fk_name,
                        schema_name=s_name,
                        sql=fk_sql,
                        target_engine=self.target_engine,
                        stage=DDLStage.FOREIGN_KEYS,
                        dependencies=(f"{s_name}.{t_name}", ref_dep),
                        safety=ConversionSafety.EXACT,
                    )
                )

        return artifacts

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(view.schema_name, view.view_name)
        sql = f"CREATE OR REPLACE VIEW {qual} AS\n{view.definition_sql};"
        return [
            StructuredDDLArtifact(
                object_type="VIEW",
                object_name=view.view_name,
                schema_name=view.schema_name,
                sql=sql,
                target_engine=self.target_engine,
                stage=DDLStage.VIEWS,
                dependencies=tuple(view.dependencies),
                safety=ConversionSafety.EXACT,
            )
        ]
