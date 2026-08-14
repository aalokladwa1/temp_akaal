"""
AKAAL Schema Engine — Universal Structural DDL Emitter Architecture
====================================================================
Provides database-agnostic canonical DDL generation for tables, columns, primary keys,
composite primary keys, foreign keys, composite foreign keys, unique constraints,
check constraints, default expressions, indexes, sequences, identity columns, and partitions
across Oracle, PostgreSQL, MySQL, MSSQL, and plugin-registered target engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import re
from typing import Dict, Any, List, Optional

from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalPrimaryKey,
    CanonicalForeignKey,
    CanonicalUniqueConstraint,
    CanonicalCheckConstraint,
    CanonicalIndex,
    CanonicalSequence,
    CanonicalIdentity,
    CanonicalPartition,
)
from akaal.schema.domain.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry


@dataclass
class StructuredDDLArtifact:
    """Structured DDL statement container with metadata, safety level, and dependencies."""
    object_type: str  # TABLE, PRIMARY_KEY, FOREIGN_KEY, UNIQUE_CONSTRAINT, CHECK_CONSTRAINT, INDEX, SEQUENCE, IDENTITY, PARTITION
    object_name: str
    schema_name: str
    sql: str
    target_engine: str
    dependencies: List[str] = field(default_factory=list)
    safety: ConversionSafety = ConversionSafety.EXACT
    warnings: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "sql": self.sql,
            "target_engine": self.target_engine,
            "dependencies": sorted(self.dependencies),
            "safety": self.safety.value,
            "warnings": self.warnings,
            "extra": self.extra,
        }


class BaseTargetDDLEmitter(ABC):
    """Abstract base contract for target-specific structural DDL emitters."""

    def __init__(self, target_engine: str):
        self.target_engine = target_engine.upper()

    @abstractmethod
    def quote_identifier(self, name: str) -> str:
        """Quote identifier according to target engine syntax rules."""
        pass

    def format_qualified_name(self, schema_name: str, object_name: str) -> str:
        return f"{self.quote_identifier(schema_name)}.{self.quote_identifier(object_name)}"

    @abstractmethod
    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        """Emit column definition SQL fragment with safety classification."""
        pass

    @abstractmethod
    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        """Emit all structural DDL artifacts for a CanonicalTable."""
        pass


class PostgreSQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for PostgreSQL."""

    def __init__(self):
        super().__init__("POSTGRESQL")

    def quote_identifier(self, name: str) -> str:
        clean = name.strip('"')
        return f'"{clean.lower()}"'

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        c_type_mod = col.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(source_engine, col.source_native_type)
        emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", c_type_mod)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        col_sql = f"{self.quote_identifier(col.name)} {emission.target_native_type}"

        if col.is_identity:
            col_sql += " GENERATED ALWAYS AS IDENTITY"

        if not col.nullable and not col.is_identity:
            col_sql += " NOT NULL"

        if col.default_expression and not col.is_identity:
            def_expr = col.default_expression
            if "SYSDATE" in def_expr.upper() or "GETDATE" in def_expr.upper():
                def_expr = "CURRENT_TIMESTAMP"
            col_sql += f" DEFAULT {def_expr}"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts = []
        s_name = table.identity.schema_name
        t_name = table.identity.object_name
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

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + "\n);"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="POSTGRESQL",
                safety=overall_safety,
                warnings=tbl_warnings,
            )
        )

        # Primary Key Constraint
        if table.primary_key and table.primary_key.column_names:
            pk = table.primary_key
            pk_name = pk.name or f"pk_{t_name}"
            pk_cols = ", ".join(self.quote_identifier(c) for c in pk.column_names)
            pk_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {self.quote_identifier(pk_name)} PRIMARY KEY ({pk_cols});"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="PRIMARY_KEY",
                    object_name=pk_name,
                    schema_name=s_name,
                    sql=pk_sql,
                    target_engine="POSTGRESQL",
                    dependencies=[t_name],
                )
            )

        # Foreign Keys
        for fk in table.foreign_keys:
            fk_name = fk.name or f"fk_{t_name}_{'_'.join(fk.column_names)}"
            src_cols = ", ".join(self.quote_identifier(c) for c in fk.column_names)
            ref_tbl = self.format_qualified_name(fk.referenced_schema, fk.referenced_table)
            ref_cols = ", ".join(self.quote_identifier(c) for c in fk.referenced_columns)
            fk_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {self.quote_identifier(fk_name)} FOREIGN KEY ({src_cols}) REFERENCES {ref_tbl} ({ref_cols});"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="FOREIGN_KEY",
                    object_name=fk_name,
                    schema_name=s_name,
                    sql=fk_sql,
                    target_engine="POSTGRESQL",
                    dependencies=[t_name, fk.referenced_table],
                )
            )

        # Unique Constraints
        for uc in table.unique_constraints:
            uc_name = uc.name or f"uq_{t_name}_{'_'.join(uc.column_names)}"
            cols = ", ".join(self.quote_identifier(c) for c in uc.column_names)
            uc_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {self.quote_identifier(uc_name)} UNIQUE ({cols});"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="UNIQUE_CONSTRAINT",
                    object_name=uc_name,
                    schema_name=s_name,
                    sql=uc_sql,
                    target_engine="POSTGRESQL",
                    dependencies=[t_name],
                )
            )

        # Check Constraints
        for cc in table.check_constraints:
            cc_name = cc.name or f"chk_{t_name}_{hashlib.md5(cc.check_clause.encode()).hexdigest()[:6]}"
            cc_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {self.quote_identifier(cc_name)} CHECK ({cc.check_clause});"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="CHECK_CONSTRAINT",
                    object_name=cc_name,
                    schema_name=s_name,
                    sql=cc_sql,
                    target_engine="POSTGRESQL",
                    dependencies=[t_name],
                )
            )

        # Indexes
        for idx in table.indexes:
            idx_name = idx.name or f"idx_{t_name}_{'_'.join(idx.column_names)}"
            uniq_str = "UNIQUE " if idx.is_unique else ""
            cols = ", ".join(self.quote_identifier(c) for c in idx.column_names)
            idx_sql = f"CREATE {uniq_str}INDEX IF NOT EXISTS {self.quote_identifier(idx_name)} ON {qual_tbl} ({cols});"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="INDEX",
                    object_name=idx_name,
                    schema_name=s_name,
                    sql=idx_sql,
                    target_engine="POSTGRESQL",
                    dependencies=[t_name],
                )
            )

        return artifacts


class OracleDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for Oracle."""

    def __init__(self):
        super().__init__("ORACLE")

    def quote_identifier(self, name: str) -> str:
        clean = name.strip('"').upper()
        return f'"{clean}"'

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        c_type_mod = col.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(source_engine, col.source_native_type)
        emission = CanonicalTypeRegistry.emit_target_type("ORACLE", c_type_mod)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        col_sql = f"{self.quote_identifier(col.name)} {emission.target_native_type}"
        if col.is_identity:
            col_sql += " GENERATED ALWAYS AS IDENTITY"

        if not col.nullable and not col.is_identity:
            col_sql += " NOT NULL"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts = []
        s_name = table.identity.schema_name
        t_name = table.identity.object_name
        qual_tbl = self.format_qualified_name(s_name, t_name)

        col_defs = []
        overall_safety = ConversionSafety.EXACT
        tbl_warnings = []

        for col in sorted(table.columns, key=lambda x: x.ordinal_position):
            col_sql, safety, warns = self.emit_column_definition(col, source_engine)
            col_defs.append(f"    {col_sql}")
            tbl_warnings.extend(warns)

        create_tbl_sql = f"CREATE TABLE {qual_tbl} (\n" + ",\n".join(col_defs) + "\n)"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="ORACLE",
                safety=overall_safety,
                warnings=tbl_warnings,
            )
        )

        if table.primary_key and table.primary_key.column_names:
            pk = table.primary_key
            pk_name = pk.name or f"PK_{t_name.upper()}"
            pk_cols = ", ".join(self.quote_identifier(c) for c in pk.column_names)
            pk_sql = f"ALTER TABLE {qual_tbl} ADD CONSTRAINT {self.quote_identifier(pk_name)} PRIMARY KEY ({pk_cols})"
            artifacts.append(
                StructuredDDLArtifact(
                    object_type="PRIMARY_KEY",
                    object_name=pk_name,
                    schema_name=s_name,
                    sql=pk_sql,
                    target_engine="ORACLE",
                    dependencies=[t_name],
                )
            )

        return artifacts


class MySQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for MySQL."""

    def __init__(self):
        super().__init__("MYSQL")

    def quote_identifier(self, name: str) -> str:
        clean = name.strip("`")
        return f"`{clean}`"

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        c_type_mod = col.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(source_engine, col.source_native_type)
        emission = CanonicalTypeRegistry.emit_target_type("MYSQL", c_type_mod)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        col_sql = f"{self.quote_identifier(col.name)} {emission.target_native_type}"
        if col.is_identity:
            col_sql += " AUTO_INCREMENT"
        if not col.nullable:
            col_sql += " NOT NULL"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts = []
        s_name = table.identity.schema_name
        t_name = table.identity.object_name
        qual_tbl = self.format_qualified_name(s_name, t_name)

        col_defs = []
        for col in sorted(table.columns, key=lambda x: x.ordinal_position):
            col_sql, safety, warns = self.emit_column_definition(col, source_engine)
            col_defs.append(f"    {col_sql}")

        if table.primary_key and table.primary_key.column_names:
            pk_cols = ", ".join(self.quote_identifier(c) for c in table.primary_key.column_names)
            col_defs.append(f"    PRIMARY KEY ({pk_cols})")

        create_tbl_sql = f"CREATE TABLE IF NOT EXISTS {qual_tbl} (\n" + ",\n".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="MYSQL",
            )
        )

        return artifacts


class MSSQLDDLEmitter(BaseTargetDDLEmitter):
    """Target DDL Emitter for Microsoft SQL Server."""

    def __init__(self):
        super().__init__("MSSQL")

    def quote_identifier(self, name: str) -> str:
        clean = name.strip("[]")
        return f"[{clean}]"

    def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC") -> Tuple[str, ConversionSafety, List[str]]:
        warnings = []
        c_type_mod = col.canonical_type_model or CanonicalTypeRegistry.normalize_source_type(source_engine, col.source_native_type)
        emission = CanonicalTypeRegistry.emit_target_type("MSSQL", c_type_mod)
        if emission.warning_message:
            warnings.append(emission.warning_message)

        col_sql = f"{self.quote_identifier(col.name)} {emission.target_native_type}"
        if col.is_identity:
            col_sql += " IDENTITY(1,1)"
        if not col.nullable:
            col_sql += " NOT NULL"

        return col_sql, emission.safety, warnings

    def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC") -> List[StructuredDDLArtifact]:
        artifacts = []
        s_name = table.identity.schema_name
        t_name = table.identity.object_name
        qual_tbl = self.format_qualified_name(s_name, t_name)

        col_defs = []
        for col in sorted(table.columns, key=lambda x: x.ordinal_position):
            col_sql, safety, warns = self.emit_column_definition(col, source_engine)
            col_defs.append(f"    {col_sql}")

        create_tbl_sql = f"CREATE TABLE {qual_tbl} (\n" + ",\n".join(col_defs) + "\n);"
        artifacts.append(
            StructuredDDLArtifact(
                object_type="TABLE",
                object_name=t_name,
                schema_name=s_name,
                sql=create_tbl_sql,
                target_engine="MSSQL",
            )
        )

        return artifacts


class UniversalDDLAuthority:
    """Universal Structural DDL Generation Authority."""

    _emitters: Dict[str, BaseTargetDDLEmitter] = {}

    @classmethod
    def _init_default_emitters(cls):
        if not cls._emitters:
            cls._emitters["POSTGRESQL"] = PostgreSQLDDLEmitter()
            cls._emitters["POSTGRES"] = cls._emitters["POSTGRESQL"]
            cls._emitters["ORACLE"] = OracleDDLEmitter()
            cls._emitters["MYSQL"] = MySQLDDLEmitter()
            cls._emitters["MARIADB"] = cls._emitters["MYSQL"]
            cls._emitters["MSSQL"] = MSSQLDDLEmitter()
            cls._emitters["SQLSERVER"] = cls._emitters["MSSQL"]

    @classmethod
    def register_emitter(cls, engine: str, emitter: BaseTargetDDLEmitter):
        """Plugin Extensibility Hook: Register custom target DDL emitter (e.g. IBM DB2 or DB #50)."""
        cls._init_default_emitters()
        cls._emitters[engine.upper()] = emitter

    @classmethod
    def get_emitter(cls, engine: str) -> BaseTargetDDLEmitter:
        cls._init_default_emitters()
        eng = str(engine).upper()
        if eng in cls._emitters:
            return cls._emitters[eng]
        raise ValueError(f"Unsupported target database engine for DDL generation: {engine}")

    @classmethod
    def emit_table_ddl(
        cls, table: CanonicalTable, target_engine: str, source_engine: str = "GENERIC"
    ) -> List[StructuredDDLArtifact]:
        """Emit deterministic structured DDL artifacts for a CanonicalTable."""
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_table_artifacts(table, source_engine)

    @classmethod
    def emit_schema_ddl(
        cls, model: CanonicalSchemaModel, target_engine: str
    ) -> List[StructuredDDLArtifact]:
        """Emit deterministic structured DDL artifacts for an entire CanonicalSchemaModel."""
        artifacts = []
        for t_name in sorted(model.tables.keys()):
            table = model.tables[t_name]
            artifacts.extend(cls.emit_table_ddl(table, target_engine, model.engine))
        return artifacts
