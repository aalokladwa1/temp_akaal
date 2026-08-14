"""
AKAAL Schema Engine — Universal Programmable Database Object Conversion Engine
=============================================================================
Provides database-agnostic conversion, AST normalization, built-in function translation,
and risk classification for Views, Materialized Views, Stored Procedures, Functions,
Triggers, and Packages across Oracle, PostgreSQL, MySQL, MSSQL, and plugin target engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple

from akaal.schema.domain.models import (
    CanonicalView,
    CanonicalMaterializedView,
    CanonicalProcedure,
    CanonicalFunction,
    CanonicalTrigger,
)
from akaal.schema.domain.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry


@dataclass
class StructuredProgrammableArtifact:
    """Container for converted programmable database object DDL with safety & evidence metadata."""
    object_type: str  # VIEW, MATERIALIZED_VIEW, PROCEDURE, FUNCTION, TRIGGER, PACKAGE
    object_name: str
    schema_name: str
    source_engine: str
    target_engine: str
    raw_source_definition: str
    target_sql: str
    conversion_status: str  # AUTOMATIC, AUTOMATIC_WITH_WARNINGS, MANUAL_REVIEW_REQUIRED, UNSUPPORTED
    safety: ConversionSafety = ConversionSafety.EXACT
    warnings: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    source_fingerprint: str = ""
    conversion_fingerprint: str = ""

    def __post_init__(self):
        if not self.source_fingerprint and self.raw_source_definition:
            self.source_fingerprint = hashlib.sha256(self.raw_source_definition.strip().encode("utf-8")).hexdigest()
        if not self.conversion_fingerprint and self.target_sql:
            self.conversion_fingerprint = hashlib.sha256(self.target_sql.strip().encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "source_engine": self.source_engine,
            "target_engine": self.target_engine,
            "target_sql": self.target_sql,
            "conversion_status": self.conversion_status,
            "safety": self.safety.value,
            "warnings": self.warnings,
            "dependencies": sorted(self.dependencies),
            "source_fingerprint": self.source_fingerprint,
            "conversion_fingerprint": self.conversion_fingerprint,
        }


class SQLRulebook:
    """Central database-agnostic expression translation rulebook."""

    @classmethod
    def translate_expressions(cls, sql_text: str, source_engine: str, target_engine: str) -> Tuple[str, List[str]]:
        """Translate built-in SQL functions and expressions across database engines."""
        src = source_engine.upper()
        tgt = target_engine.upper()
        res = sql_text
        warnings = []

        # 1. Null handling functions (NVL / ISNULL -> COALESCE)
        if src in ("ORACLE", "MSSQL") and tgt in ("POSTGRESQL", "POSTGRES", "MYSQL"):
            res = re.sub(r"\bNVL\s*\(", "COALESCE(", res, flags=re.IGNORECASE)
            res = re.sub(r"\bISNULL\s*\(", "COALESCE(", res, flags=re.IGNORECASE)

        # 2. Date / Time functions (SYSDATE / GETDATE() -> CURRENT_TIMESTAMP)
        if src == "ORACLE" and "SYSDATE" in res.upper():
            res = re.sub(r"\bSYSDATE\b", "CURRENT_TIMESTAMP", res, flags=re.IGNORECASE)
        elif src in ("MSSQL", "SQLSERVER") and "GETDATE()" in res.upper():
            res = re.sub(r"\bGETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP", res, flags=re.IGNORECASE)

        # 3. Trigger pseudo-tables (:NEW / :OLD -> NEW / OLD or inserted / deleted)
        if tgt in ("POSTGRESQL", "POSTGRES", "MYSQL"):
            res = re.sub(r":NEW\b", "NEW", res, flags=re.IGNORECASE)
            res = re.sub(r":OLD\b", "OLD", res, flags=re.IGNORECASE)
        elif tgt in ("MSSQL", "SQLSERVER"):
            res = re.sub(r":NEW\b|\bNEW\b", "inserted", res, flags=re.IGNORECASE)
            res = re.sub(r":OLD\b|\bOLD\b", "deleted", res, flags=re.IGNORECASE)

        # 4. Check for dynamic SQL
        if any(kw in res.upper() for kw in ("EXECUTE IMMEDIATE", "SP_EXECUTESQL", "PREPARE")):
            warnings.append("Dynamic SQL detected in programmable body; manual verification required")

        # 5. Check for autonomous transactions or explicit commits
        if "PRAGMA AUTONOMOUS_TRANSACTION" in res.upper() or "COMMIT" in res.upper():
            warnings.append("Autonomous transaction or explicit COMMIT detected in programmable body")

        return res, warnings


class BaseProgrammableEmitter(ABC):
    """Abstract base contract for target programmable object emitters."""

    def __init__(self, target_engine: str):
        self.target_engine = target_engine.upper()

    @abstractmethod
    def emit_view(self, view: CanonicalView, source_engine: str) -> StructuredProgrammableArtifact:
        pass

    @abstractmethod
    def emit_materialized_view(self, mv: CanonicalMaterializedView, source_engine: str) -> StructuredProgrammableArtifact:
        pass

    @abstractmethod
    def emit_procedure(self, proc: CanonicalProcedure, source_engine: str) -> StructuredProgrammableArtifact:
        pass

    @abstractmethod
    def emit_function(self, func: CanonicalFunction, source_engine: str) -> StructuredProgrammableArtifact:
        pass

    @abstractmethod
    def emit_trigger(self, trig: CanonicalTrigger, source_engine: str) -> StructuredProgrammableArtifact:
        pass


class PostgreSQLProgrammableEmitter(BaseProgrammableEmitter):
    """Target Programmable Emitter for PostgreSQL."""

    def __init__(self):
        super().__init__("POSTGRESQL")

    def emit_view(self, view: CanonicalView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = view.source_definition or f"SELECT * FROM {view.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "POSTGRESQL")
        sql = f'CREATE OR REPLACE VIEW "{view.schema_name}"."{view.name}" AS\n{translated_query.strip()};'

        status = "AUTOMATIC_WITH_WARNINGS" if warnings else "AUTOMATIC"
        safety = ConversionSafety.SAFE if warnings else ConversionSafety.EXACT

        return StructuredProgrammableArtifact(
            object_type="VIEW",
            object_name=view.name,
            schema_name=view.schema_name,
            source_engine=source_engine,
            target_engine="POSTGRESQL",
            raw_source_definition=raw,
            target_sql=sql,
            conversion_status=status,
            safety=safety,
            warnings=warnings,
            dependencies=view.dependencies or [],
        )

    def emit_materialized_view(self, mv: CanonicalMaterializedView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = mv.source_definition or f"SELECT * FROM {mv.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "POSTGRESQL")
        sql = f'CREATE MATERIALIZED VIEW IF NOT EXISTS "{mv.schema_name}"."{mv.name}" AS\n{translated_query.strip()};'

        return StructuredProgrammableArtifact(
            object_type="MATERIALIZED_VIEW",
            object_name=mv.name,
            schema_name=mv.schema_name,
            source_engine=source_engine,
            target_engine="POSTGRESQL",
            raw_source_definition=raw,
            target_sql=sql,
            conversion_status="AUTOMATIC" if not warnings else "AUTOMATIC_WITH_WARNINGS",
            safety=ConversionSafety.EXACT if not warnings else ConversionSafety.SAFE,
            warnings=warnings,
            dependencies=[],
        )

    def emit_procedure(self, proc: CanonicalProcedure, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = proc.source_definition or "BEGIN NULL; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "POSTGRESQL")

        has_complex = any(kw in raw_body.upper() for kw in ("EXECUTE IMMEDIATE", "PACKAGE", "PRAGMA", "EXCEPTION"))
        status = "MANUAL_REVIEW_REQUIRED" if has_complex else ("AUTOMATIC_WITH_WARNINGS" if warnings else "AUTOMATIC")
        safety = ConversionSafety.POTENTIALLY_LOSSY if has_complex else ConversionSafety.SAFE

        if has_complex:
            warnings.append("Complex procedural constructs require manual review in target PL/pgSQL")
            target_sql = f'-- MANUAL REVIEW REQUIRED FOR PROCEDURE "{proc.schema_name}"."{proc.name}"\n-- SOURCE DEFINITION:\n/*\n{raw_body}\n*/\nCREATE OR REPLACE PROCEDURE "{proc.schema_name}"."{proc.name}"()\nLANGUAGE plpgsql AS $$\nBEGIN\n    -- TODO: Review converted PL/pgSQL body\n    {translated_body.strip()}\nEND;\n$$;'
        else:
            target_sql = f'CREATE OR REPLACE PROCEDURE "{proc.schema_name}"."{proc.name}"()\nLANGUAGE plpgsql AS $$\nBEGIN\n    {translated_body.strip()}\nEND;\n$$;'

        return StructuredProgrammableArtifact(
            object_type="PROCEDURE",
            object_name=proc.name,
            schema_name=proc.schema_name,
            source_engine=source_engine,
            target_engine="POSTGRESQL",
            raw_source_definition=raw_body,
            target_sql=target_sql,
            conversion_status=status,
            safety=safety,
            warnings=warnings,
            dependencies=[],
        )

    def emit_function(self, func: CanonicalFunction, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = func.source_definition or "RETURN NULL;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "POSTGRESQL")

        ret_type_mod = CanonicalTypeRegistry.normalize_source_type(source_engine, func.return_type or "VARCHAR")
        ret_type = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", ret_type_mod).target_native_type

        target_sql = f'CREATE OR REPLACE FUNCTION "{func.schema_name}"."{func.name}"()\nRETURNS {ret_type} LANGUAGE plpgsql AS $$\nBEGIN\n    {translated_body.strip()}\nEND;\n$$;'

        return StructuredProgrammableArtifact(
            object_type="FUNCTION",
            object_name=func.name,
            schema_name=func.schema_name,
            source_engine=source_engine,
            target_engine="POSTGRESQL",
            raw_source_definition=raw_body,
            target_sql=target_sql,
            conversion_status="AUTOMATIC" if not warnings else "AUTOMATIC_WITH_WARNINGS",
            safety=ConversionSafety.EXACT if not warnings else ConversionSafety.SAFE,
            warnings=warnings,
            dependencies=[],
        )

    def emit_trigger(self, trig: CanonicalTrigger, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = trig.source_definition or "BEGIN NULL; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "POSTGRESQL")

        fn_name = f"trg_fn_{trig.name}"
        fn_sql = f'CREATE OR REPLACE FUNCTION "{trig.schema_name}"."{fn_name}"()\nRETURNS trigger LANGUAGE plpgsql AS $$\nBEGIN\n    {translated_body.strip()}\n    RETURN NEW;\nEND;\n$$;'

        timing = trig.timing.upper() if trig.timing else "BEFORE"
        event = trig.events[0].upper() if trig.events else "INSERT"
        trig_sql = f'{fn_sql}\nCREATE TRIGGER "{trig.name}" {timing} {event} ON "{trig.schema_name}"."{trig.table_name}"\nFOR EACH ROW EXECUTE FUNCTION "{trig.schema_name}"."{fn_name}"();'

        return StructuredProgrammableArtifact(
            object_type="TRIGGER",
            object_name=trig.name,
            schema_name=trig.schema_name,
            source_engine=source_engine,
            target_engine="POSTGRESQL",
            raw_source_definition=raw_body,
            target_sql=trig_sql,
            conversion_status="AUTOMATIC" if not warnings else "AUTOMATIC_WITH_WARNINGS",
            safety=ConversionSafety.SAFE,
            warnings=warnings,
            dependencies=[trig.table_name],
        )


class OracleProgrammableEmitter(BaseProgrammableEmitter):
    """Target Programmable Emitter for Oracle."""

    def __init__(self):
        super().__init__("ORACLE")

    def emit_view(self, view: CanonicalView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = view.source_definition or f"SELECT * FROM {view.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "ORACLE")
        sql = f'CREATE OR REPLACE VIEW "{view.schema_name.upper()}"."{view.name.upper()}" AS\n{translated_query.strip()}'
        return StructuredProgrammableArtifact("VIEW", view.name, view.schema_name, source_engine, "ORACLE", raw, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_materialized_view(self, mv: CanonicalMaterializedView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = mv.source_definition or f"SELECT * FROM {mv.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "ORACLE")
        sql = f'CREATE MATERIALIZED VIEW "{mv.schema_name.upper()}"."{mv.name.upper()}" AS\n{translated_query.strip()}'
        return StructuredProgrammableArtifact("MATERIALIZED_VIEW", mv.name, mv.schema_name, source_engine, "ORACLE", raw, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_procedure(self, proc: CanonicalProcedure, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = proc.source_definition or "BEGIN NULL; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "ORACLE")
        sql = f'CREATE OR REPLACE PROCEDURE "{proc.schema_name.upper()}"."{proc.name.upper()}" AS\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("PROCEDURE", proc.name, proc.schema_name, source_engine, "ORACLE", raw_body, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_function(self, func: CanonicalFunction, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = func.source_definition or "RETURN NULL;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "ORACLE")
        ret_type_mod = CanonicalTypeRegistry.normalize_source_type(source_engine, func.return_type or "VARCHAR2")
        ret_type = CanonicalTypeRegistry.emit_target_type("ORACLE", ret_type_mod).target_native_type
        sql = f'CREATE OR REPLACE FUNCTION "{func.schema_name.upper()}"."{func.name.upper()}" RETURN {ret_type} AS\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("FUNCTION", func.name, func.schema_name, source_engine, "ORACLE", raw_body, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_trigger(self, trig: CanonicalTrigger, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = trig.source_definition or "BEGIN NULL; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "ORACLE")
        event = trig.events[0].upper() if trig.events else "INSERT"
        sql = f'CREATE OR REPLACE TRIGGER "{trig.schema_name.upper()}"."{trig.name.upper()}"\n{trig.timing or "BEFORE"} {event} ON "{trig.schema_name.upper()}"."{trig.table_name.upper()}"\nFOR EACH ROW\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("TRIGGER", trig.name, trig.schema_name, source_engine, "ORACLE", raw_body, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)


class MySQLProgrammableEmitter(BaseProgrammableEmitter):
    """Target Programmable Emitter for MySQL."""

    def __init__(self):
        super().__init__("MYSQL")

    def emit_view(self, view: CanonicalView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = view.source_definition or f"SELECT * FROM {view.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "MYSQL")
        sql = f'CREATE OR REPLACE VIEW `{view.schema_name}`.`{view.name}` AS\n{translated_query.strip()};'
        return StructuredProgrammableArtifact("VIEW", view.name, view.schema_name, source_engine, "MYSQL", raw, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_materialized_view(self, mv: CanonicalMaterializedView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = mv.source_definition or f"SELECT * FROM {mv.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "MYSQL")
        warnings.append("MySQL does not natively support MATERIALIZED VIEW; emitted as standard VIEW")
        sql = f'CREATE OR REPLACE VIEW `{mv.schema_name}`.`{mv.name}` AS\n{translated_query.strip()};'
        return StructuredProgrammableArtifact("MATERIALIZED_VIEW", mv.name, mv.schema_name, source_engine, "MYSQL", raw, sql, "AUTOMATIC_WITH_WARNINGS", ConversionSafety.POTENTIALLY_LOSSY, warnings)

    def emit_procedure(self, proc: CanonicalProcedure, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = proc.source_definition or "BEGIN END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MYSQL")
        sql = f'CREATE PROCEDURE `{proc.schema_name}`.`{proc.name}`()\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("PROCEDURE", proc.name, proc.schema_name, source_engine, "MYSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)

    def emit_function(self, func: CanonicalFunction, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = func.source_definition or "RETURN NULL;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MYSQL")
        ret_type_mod = CanonicalTypeRegistry.normalize_source_type(source_engine, func.return_type or "VARCHAR")
        ret_type = CanonicalTypeRegistry.emit_target_type("MYSQL", ret_type_mod).target_native_type
        sql = f'CREATE FUNCTION `{func.schema_name}`.`{func.name}`()\nRETURNS {ret_type} DETERMINISTIC\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("FUNCTION", func.name, func.schema_name, source_engine, "MYSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)

    def emit_trigger(self, trig: CanonicalTrigger, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = trig.source_definition or "BEGIN END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MYSQL")
        event = trig.events[0].upper() if trig.events else "INSERT"
        sql = f'CREATE TRIGGER `{trig.name}` {trig.timing or "BEFORE"} {event} ON `{trig.schema_name}`.`{trig.table_name}`\nFOR EACH ROW\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("TRIGGER", trig.name, trig.schema_name, source_engine, "MYSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)


class MSSQLProgrammableEmitter(BaseProgrammableEmitter):
    """Target Programmable Emitter for Microsoft SQL Server."""

    def __init__(self):
        super().__init__("MSSQL")

    def emit_view(self, view: CanonicalView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = view.source_definition or f"SELECT * FROM {view.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "MSSQL")
        sql = f'CREATE OR ALTER VIEW [{view.schema_name}].[{view.name}] AS\n{translated_query.strip()};'
        return StructuredProgrammableArtifact("VIEW", view.name, view.schema_name, source_engine, "MSSQL", raw, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_materialized_view(self, mv: CanonicalMaterializedView, source_engine: str) -> StructuredProgrammableArtifact:
        raw = mv.source_definition or f"SELECT * FROM {mv.name}"
        translated_query, warnings = SQLRulebook.translate_expressions(raw, source_engine, "MSSQL")
        sql = f'CREATE OR ALTER VIEW [{mv.schema_name}].[{mv.name}] WITH SCHEMABINDING AS\n{translated_query.strip()};'
        return StructuredProgrammableArtifact("MATERIALIZED_VIEW", mv.name, mv.schema_name, source_engine, "MSSQL", raw, sql, "AUTOMATIC", ConversionSafety.EXACT, warnings)

    def emit_procedure(self, proc: CanonicalProcedure, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = proc.source_definition or "BEGIN RETURN; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MSSQL")
        sql = f'CREATE OR ALTER PROCEDURE [{proc.schema_name}].[{proc.name}]\nAS\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("PROCEDURE", proc.name, proc.schema_name, source_engine, "MSSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)

    def emit_function(self, func: CanonicalFunction, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = func.source_definition or "RETURN NULL;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MSSQL")
        ret_type_mod = CanonicalTypeRegistry.normalize_source_type(source_engine, func.return_type or "NVARCHAR")
        ret_type = CanonicalTypeRegistry.emit_target_type("MSSQL", ret_type_mod).target_native_type
        sql = f'CREATE OR ALTER FUNCTION [{func.schema_name}].[{func.name}]()\nRETURNS {ret_type} AS\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("FUNCTION", func.name, func.schema_name, source_engine, "MSSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)

    def emit_trigger(self, trig: CanonicalTrigger, source_engine: str) -> StructuredProgrammableArtifact:
        raw_body = trig.source_definition or "BEGIN RETURN; END;"
        translated_body, warnings = SQLRulebook.translate_expressions(raw_body, source_engine, "MSSQL")
        event = trig.events[0].upper() if trig.events else "INSERT"
        sql = f'CREATE OR ALTER TRIGGER [{trig.name}] ON [{trig.schema_name}].[{trig.table_name}]\nAFTER {event}\nAS\nBEGIN\n    {translated_body.strip()}\nEND;'
        return StructuredProgrammableArtifact("TRIGGER", trig.name, trig.schema_name, source_engine, "MSSQL", raw_body, sql, "AUTOMATIC", ConversionSafety.SAFE, warnings)


class CanonicalProgrammableAuthority:
    """Universal Canonical Programmable Database Object Authority."""

    _emitters: Dict[str, BaseProgrammableEmitter] = {}

    @classmethod
    def _init_default_emitters(cls):
        if not cls._emitters:
            cls._emitters["POSTGRESQL"] = PostgreSQLProgrammableEmitter()
            cls._emitters["POSTGRES"] = cls._emitters["POSTGRESQL"]
            cls._emitters["ORACLE"] = OracleProgrammableEmitter()
            cls._emitters["MYSQL"] = MySQLProgrammableEmitter()
            cls._emitters["MARIADB"] = cls._emitters["MYSQL"]
            cls._emitters["MSSQL"] = MSSQLProgrammableEmitter()
            cls._emitters["SQLSERVER"] = cls._emitters["MSSQL"]

    @classmethod
    def register_emitter(cls, engine: str, emitter: BaseProgrammableEmitter):
        """Plugin Extensibility Hook: Register custom target programmable emitter (e.g. IBM DB2 or DB #50)."""
        cls._init_default_emitters()
        cls._emitters[engine.upper()] = emitter

    @classmethod
    def get_emitter(cls, engine: str) -> BaseProgrammableEmitter:
        cls._init_default_emitters()
        eng = str(engine).upper()
        if eng in cls._emitters:
            return cls._emitters[eng]
        raise ValueError(f"Unsupported target database engine for programmable conversion: {engine}")

    @classmethod
    def convert_view(cls, view: CanonicalView, target_engine: str, source_engine: str = "GENERIC") -> StructuredProgrammableArtifact:
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_view(view, source_engine)

    @classmethod
    def convert_materialized_view(cls, mv: CanonicalMaterializedView, target_engine: str, source_engine: str = "GENERIC") -> StructuredProgrammableArtifact:
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_materialized_view(mv, source_engine)

    @classmethod
    def convert_procedure(cls, proc: CanonicalProcedure, target_engine: str, source_engine: str = "GENERIC") -> StructuredProgrammableArtifact:
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_procedure(proc, source_engine)

    @classmethod
    def convert_function(cls, func: CanonicalFunction, target_engine: str, source_engine: str = "GENERIC") -> StructuredProgrammableArtifact:
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_function(func, source_engine)

    @classmethod
    def convert_trigger(cls, trig: CanonicalTrigger, target_engine: str, source_engine: str = "GENERIC") -> StructuredProgrammableArtifact:
        emitter = cls.get_emitter(target_engine)
        return emitter.emit_trigger(trig, source_engine)
