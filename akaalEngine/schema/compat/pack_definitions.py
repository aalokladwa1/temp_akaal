"""
akaalEngine.schema.compat.pack_definitions
==========================================
Structured definitions and DDL specifications for the `akaal_compat` emulation schema helpers.
Provides drop-in compatibility functions for Oracle/MSSQL constructs migrated to PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class CompatibilityFunctionDef:
    """Specification of an emulation helper function."""
    function_name: str
    target_schema: str = "akaal_compat"
    signature: str = ""
    return_type: str = ""
    definition_sql: str = ""
    description: str = ""
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    @property
    def qualified_name(self) -> str:
        return f"{self.target_schema}.{self.function_name}"


class CompatibilityPackDefinitions:
    """Catalog of canonical akaal_compat helper functions for PostgreSQL."""

    _PACK: Dict[str, CompatibilityFunctionDef] = {
        "nvl": CompatibilityFunctionDef(
            function_name="nvl",
            signature="(val ANYELEMENT, default_val ANYELEMENT)",
            return_type="ANYELEMENT",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat.nvl(val ANYELEMENT, default_val ANYELEMENT)
RETURNS ANYELEMENT IMMUTABLE LANGUAGE sql AS $$
    SELECT COALESCE(val, default_val);
$$;""",
            description="Oracle NVL emulation returning first non-null argument",
        ),
        "decode": CompatibilityFunctionDef(
            function_name="decode",
            signature="(val ANYELEMENT, opt1 ANYELEMENT, res1 ANYELEMENT, default_res ANYELEMENT)",
            return_type="ANYELEMENT",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat.decode(val ANYELEMENT, opt1 ANYELEMENT, res1 ANYELEMENT, default_res ANYELEMENT)
RETURNS ANYELEMENT IMMUTABLE LANGUAGE sql AS $$
    SELECT CASE WHEN val = opt1 THEN res1 ELSE default_res END;
$$;""",
            description="Oracle simple DECODE emulation",
        ),
        "trunc_date": CompatibilityFunctionDef(
            function_name="trunc_date",
            signature="(dt TIMESTAMP)",
            return_type="DATE",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat.trunc_date(dt TIMESTAMP)
RETURNS DATE IMMUTABLE LANGUAGE sql AS $$
    SELECT dt::date;
$$;""",
            description="Oracle TRUNC(date) day truncation emulation",
        ),
        "instr": CompatibilityFunctionDef(
            function_name="instr",
            signature="(str TEXT, substr TEXT)",
            return_type="INTEGER",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat.instr(str TEXT, substr TEXT)
RETURNS INTEGER IMMUTABLE LANGUAGE sql AS $$
    SELECT POSITION(substr IN str);
$$;""",
            description="Oracle INSTR 2-argument substring position emulation",
        ),
        "sys_guid": CompatibilityFunctionDef(
            function_name="sys_guid",
            signature="()",
            return_type="RAW",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat.sys_guid()
RETURNS BYTEA VOLATILE LANGUAGE sql AS $$
    SELECT decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
$$;""",
            description="Oracle SYS_GUID 16-byte raw UUID generator emulation",
        ),
        "dbms_output_put_line": CompatibilityFunctionDef(
            function_name="put_line",
            target_schema="akaal_compat_dbms_output",
            signature="(msg TEXT)",
            return_type="VOID",
            definition_sql="""CREATE OR REPLACE FUNCTION akaal_compat_dbms_output.put_line(msg TEXT)
RETURNS VOID VOLATILE LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE '%', msg;
END;
$$;""",
            description="Oracle DBMS_OUTPUT.PUT_LINE emulation via RAISE NOTICE",
        ),
    }

    @classmethod
    def get_function(cls, name: str) -> Optional[CompatibilityFunctionDef]:
        return cls._PACK.get(name.lower())

    @classmethod
    def get_all_definitions(cls) -> List[CompatibilityFunctionDef]:
        return list(cls._PACK.values())

    @classmethod
    def generate_install_script(cls) -> str:
        """Generates full SQL installation script for akaal_compat schema and functions."""
        lines = [
            "-- ========================================================",
            "-- AKAAL COMPATIBILITY PACK INITIALIZATION",
            "-- ========================================================",
            "CREATE SCHEMA IF NOT EXISTS akaal_compat;",
            "CREATE SCHEMA IF NOT EXISTS akaal_compat_dbms_output;\n",
        ]
        for fn in cls._PACK.values():
            lines.append(fn.definition_sql)
            lines.append("")
        return "\n".join(lines)
