"""
akaalEngine.schema.ddl.providers.postgresql
===========================================
Target DDL emitter for PostgreSQL.
Generates syntax-exact DDL for schemas, types, sequences, tables, constraints, indexes, and views.
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


class PostgreSQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for PostgreSQL."""

    def __init__(self):
        super().__init__("POSTGRESQL")

    def quote(self, name: str) -> str:
        return IdentifierSanitizer.quote_identifier(IdentifierSanitizer.sanitize_identifier(name, "POSTGRESQL"), "POSTGRESQL")

    def format_qualified_name(self, schema_name: Optional[str], object_name: str) -> str:
        return IdentifierSanitizer.format_qualified_name(schema_name, object_name, "POSTGRESQL")

    def emit_schema_artifacts(self, schema_name: str) -> List[StructuredDDLArtifact]:
        q_schema = self.quote(schema_name)
        sql = f"CREATE SCHEMA IF NOT EXISTS {q_schema};"
        return [
            StructuredDDLArtifact(
                object_type="SCHEMA",
                object_name=schema_name,
                schema_name=schema_name,
                sql=sql,
                target_engine="POSTGRESQL",
                stage=DDLStage.SCHEMAS,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_sequence_artifacts(self, sequence: CanonicalSequence) -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(sequence.schema_name, sequence.name)
        parts = [f"CREATE SEQUENCE IF NOT EXISTS {qual}"]
        parts.append(f"    START WITH {sequence.start_value}")
        parts.append(f"    INCREMENT BY {sequence.increment_by}")
        if sequence.min_value is not None:
            parts.append(f"    MINVALUE {sequence.min_value}")
        if sequence.max_value is not None:
            parts.append(f"    MAXVALUE {sequence.max_value}")
        if sequence.is_cycling:
            parts.append("    CYCLE")
        else:
            parts.append("    NO CYCLE")
        if sequence.cache_size > 1:
            parts.append(f"    CACHE {sequence.cache_size}")
        sql = "\n".join(parts) + ";"
        return [
            StructuredDDLArtifact(
                object_type="SEQUENCE",
                object_name=sequence.name,
                schema_name=sequence.schema_name,
                sql=sql,
                target_engine="POSTGRESQL",
                stage=DDLStage.SEQUENCES,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_udt_artifacts(self, udt: CanonicalUDT) -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(udt.schema_name, udt.name)
        if udt.udt_type.upper() == "ENUM" and udt.enum_values:
            quoted_vals = [f"'{v}'" for v in udt.enum_values]
            sql = f"DO $$\nBEGIN\n    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{udt.name.lower()}') THEN\n        CREATE TYPE {qual} AS ENUM ({', '.join(quoted_vals)});\n    END IF;\nEND$$;"
        elif udt.udt_type.upper() == "COMPOSITE" and udt.attributes:
            attr_defs = []
            for attr_name, attr_type in udt.attributes.items():
                attr_defs.append(f"    {self.quote(attr_name)} {attr_type}")
            sql = f"CREATE TYPE {qual} AS (\n" + ",\n".join(attr_defs) + "\n);"
        elif udt.udt_type.upper() == "DOMAIN" and udt.underlying_type:
            check_part = f" {udt.base_check_clause}" if udt.base_check_clause else ""
            sql = f"CREATE DOMAIN {qual} AS {udt.underlying_type}{check_part};"
        else:
            return []

        return [
            StructuredDDLArtifact(
                object_type="UDT",
                object_name=udt.name,
                schema_name=udt.schema_name,
                sql=sql,
                target_engine="POSTGRESQL",
                stage=DDLStage.TYPES,
                safety=ConversionSafety.EXACT,
            )
        ]

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", col.canonical_type)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        q_name = self.quote(col.name)
        col_sql = f"{q_name} {emission.target_native_type}"

        if col.is_identity:
            gen = col.identity_generation or "BY DEFAULT"
            col_sql += f" GENERATED {gen} AS IDENTITY"

        if not col.nullable and not col.is_identity:
            col_sql += " NOT NULL"

        if col.default_expression and not col.is_identity:
            col_sql += f" DEFAULT {col.default_expression}"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts: List[StructuredDDLArtifact] = []
        s_name = table.schema_name or "public"
        t_name = table.table_name
        qual_tbl = self.format_qualified_name(s_name, t_name)

        # 1. Base Table Definition (Columns + Inline PK / Unique / Check)
        col_defs = []
        overall_safety = ConversionSafety.EXACT
        tbl_warnings = []

        for col in sorted(table.columns, key=lambda x: x.ordinal_position):
            col_sql, safety, warns = self.emit_column_definition(col, source_engine)
            col_defs.append(f"    {col_sql}")
            if safety != ConversionSafety.EXACT and overall_safety == ConversionSafety.EXACT:
                overall_safety = safety
            tbl_warnings.extend(warns)

        # Primary Key (Inline if simple, or table constraint)
        if table.primary_key and table.primary_key.columns:
            pk_cols = [self.quote(c) for c in table.primary_key.columns]
            pk_name_sql = f"CONSTRAINT {self.quote(table.primary_key.name)} " if table.primary_key.name else ""
            col_defs.append(f"    {pk_name_sql}PRIMARY KEY ({', '.join(pk_cols)})")

        # Unique Constraints
        for uc in table.unique_constraints:
            if uc.columns:
                uc_cols = [self.quote(c) for c in uc.columns]
                uc_name_sql = f"CONSTRAINT {self.quote(uc.name)} " if uc.name else ""
                col_defs.append(f"    {uc_name_sql}UNIQUE ({', '.join(uc_cols)})")

        # Check Constraints
        for ck in table.check_constraints:
            if ck.check_clause:
                ck_name_sql = f"CONSTRAINT {self.quote(ck.name)} " if ck.name else ""
                col_defs.append(f"    {ck_name_sql}CHECK ({ck.check_clause})")

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + "\n);"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="POSTGRESQL",
                stage=DDLStage.TABLES,
                safety=overall_safety,
                warnings=tuple(tbl_warnings),
            )
        )

        # 2. Indexes (Stage: INDEXES)
        for idx in table.indexes:
            if idx.columns or idx.expression:
                q_idx = self.quote(idx.name)
                unique_str = "UNIQUE " if idx.is_unique else ""
                method_str = f"USING {idx.access_method.value.lower()} " if idx.access_method else ""
                
                if idx.expression:
                    cols_str = f"({idx.expression})"
                else:
                    cols_str = f"({', '.join([self.quote(c) for c in idx.columns])})"

                include_str = ""
                if idx.included_columns:
                    include_str = f" INCLUDE ({', '.join([self.quote(c) for c in idx.included_columns])})"

                where_str = f" WHERE {idx.predicate_expression}" if idx.predicate_expression else ""
                idx_sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {q_idx} ON {qual_tbl} {method_str}{cols_str}{include_str}{where_str};"

                artifacts.append(
                    StructuredDDLArtifact(
                        object_type="INDEX",
                        object_name=idx.name,
                        schema_name=s_name,
                        sql=idx_sql,
                        target_engine="POSTGRESQL",
                        stage=DDLStage.INDEXES,
                        dependencies=(f"{s_name}.{t_name}",),
                        safety=ConversionSafety.EXACT,
                    )
                )

        # 3. Foreign Keys (Stage: FOREIGN_KEYS - Staged to break circular dependencies)
        for fk in table.foreign_keys:
            if fk.columns and fk.referenced_columns:
                fk_name = fk.name or f"fk_{t_name}_{'_'.join(fk.columns)}"
                q_fk = self.quote(fk_name)
                cols = ", ".join([self.quote(c) for c in fk.columns])
                ref_tbl = self.format_qualified_name(fk.referenced_schema, fk.referenced_table)
                ref_cols = ", ".join([self.quote(c) for c in fk.referenced_columns])
                actions = f" ON UPDATE {fk.on_update} ON DELETE {fk.on_delete}"
                defer_str = " DEFERRABLE" if fk.is_deferrable else ""
                if fk.is_initially_deferred:
                    defer_str += " INITIALLY DEFERRED"

                fk_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {q_fk} FOREIGN KEY ({cols}) REFERENCES {ref_tbl} ({ref_cols}){actions}{defer_str};"
                ref_dep = f"{fk.referenced_schema}.{fk.referenced_table}"

                artifacts.append(
                    StructuredDDLArtifact(
                        object_type="FOREIGN_KEY",
                        object_name=fk_name,
                        schema_name=s_name,
                        sql=fk_sql,
                        target_engine="POSTGRESQL",
                        stage=DDLStage.FOREIGN_KEYS,
                        dependencies=(f"{s_name}.{t_name}", ref_dep),
                        safety=ConversionSafety.EXACT,
                    )
                )

        return artifacts

    def emit_view_artifacts(self, view: CanonicalView, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        qual = self.format_qualified_name(view.schema_name, view.view_name)
        mat_str = "MATERIALIZED " if view.is_materialized else ""
        sql = f"CREATE OR REPLACE {mat_str}VIEW {qual} AS\n{view.definition_sql};"
        return [
            StructuredDDLArtifact(
                object_type="VIEW" if not view.is_materialized else "MATERIALIZED_VIEW",
                object_name=view.view_name,
                schema_name=view.schema_name,
                sql=sql,
                target_engine="POSTGRESQL",
                stage=DDLStage.VIEWS,
                dependencies=tuple(view.dependencies),
                safety=ConversionSafety.EXACT,
            )
        ]
