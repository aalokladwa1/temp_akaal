"""
AKAAL Schema Engine — Universal Canonical Datatype Registry & Rulebook
======================================================================
Provides source-native type normalization, target-native type emission, and risk safety
classification across Oracle, PostgreSQL, MySQL, MSSQL, and plugin-registered engines.
"""

import re
from typing import Dict, Any, Optional, Tuple, Callable
from akaal.schema.domain.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)


class CanonicalTypeRegistry:
    """Universal Datatype Registry & Conversion Rulebook."""

    _custom_normalizers: Dict[str, Callable] = {}
    _custom_emitters: Dict[str, Callable] = {}

    @classmethod
    def register_normalizer(
        cls, engine: str, func: Callable[[str, Optional[int], Optional[int], Optional[int]], CanonicalType]
    ) -> None:
        """Register a custom source type normalizer for an engine (e.g. IBM DB2 or DB #50)."""
        cls._custom_normalizers[engine.upper()] = func

    @classmethod
    def register_emitter(cls, engine: str, func: Callable[[CanonicalType], TargetTypeEmission]) -> None:
        """Register a custom target type emitter for an engine (e.g. IBM DB2 or DB #50)."""
        cls._custom_emitters[engine.upper()] = func

    @classmethod
    def normalize_source_type(
        cls,
        engine: str,
        raw_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> CanonicalType:
        """Normalize a database source native type into an AKAAL CanonicalType."""
        eng = str(engine).upper()
        raw = str(raw_type).strip().upper()

        if eng in cls._custom_normalizers:
            return cls._custom_normalizers[eng](raw, length, precision, scale)

        inline_p, inline_s, inline_l = cls._parse_type_params(raw)
        p = precision if precision is not None else inline_p
        s = scale if scale is not None else inline_s
        l = length if length is not None else inline_l

        if eng == "ORACLE":
            return cls._normalize_oracle(raw, l, p, s)
        elif eng in ("POSTGRESQL", "POSTGRES"):
            return cls._normalize_postgresql(raw, l, p, s)
        elif eng in ("MYSQL", "MARIADB"):
            return cls._normalize_mysql(raw, l, p, s, extra_metadata)
        elif eng in ("MSSQL", "SQLSERVER"):
            return cls._normalize_mssql(raw, l, p, s)
        elif eng in ("IBM_DB2", "DB2"):
            return cls._normalize_db2(raw, l, p, s)
        else:
            return CanonicalType(
                category=CanonicalTypeCategory.UNKNOWN,
                raw_vendor_type=raw_type,
                length=l,
                precision=p,
                scale=s,
            )

    @classmethod
    def emit_target_type(cls, target_engine: str, canonical_type: CanonicalType) -> TargetTypeEmission:
        """Emit target native type SQL string and safety classification from CanonicalType."""
        eng = str(target_engine).upper()

        if eng in cls._custom_emitters:
            return cls._custom_emitters[eng](canonical_type)

        if eng in ("POSTGRESQL", "POSTGRES"):
            return cls._emit_postgresql(canonical_type)
        elif eng == "ORACLE":
            return cls._emit_oracle(canonical_type)
        elif eng in ("MYSQL", "MARIADB"):
            return cls._emit_mysql(canonical_type)
        elif eng in ("MSSQL", "SQLSERVER"):
            return cls._emit_mssql(canonical_type)
        elif eng in ("IBM_DB2", "DB2"):
            return cls._emit_db2(canonical_type)
        else:
            return TargetTypeEmission(
                target_engine=target_engine,
                target_native_type="TEXT",
                safety=ConversionSafety.UNSUPPORTED,
                warning_message=f"Unsupported target database engine: {target_engine}",
            )

    @classmethod
    def convert_type(
        cls,
        source_engine: str,
        target_engine: str,
        raw_source_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> TargetTypeEmission:
        """2-Step Canonical Type Conversion: Source Native -> CanonicalType -> Target Native."""
        canon = cls.normalize_source_type(source_engine, raw_source_type, length, precision, scale, extra_metadata)
        return cls.emit_target_type(target_engine, canon)

    @staticmethod
    def _parse_type_params(raw: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        match = re.search(r"\(([\d\s,\-]+)\)", raw)
        if not match:
            return None, None, None
        parts = [p.strip() for p in match.group(1).split(",")]
        try:
            if len(parts) == 2:
                return int(parts[0]), int(parts[1]), None
            elif len(parts) == 1:
                val = int(parts[0])
                return None, None, val
        except ValueError:
            pass
        return None, None, None

    # ------------------------------------------------------------------
    # Source Normalizers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_oracle(raw: str, l: Optional[int], p: Optional[int], s: Optional[int]) -> CanonicalType:
        if "NUMBER" in raw:
            if p is not None and s is not None and s <= 0:
                bits = 64 if p > 9 else 32
                return CanonicalType(
                    category=CanonicalTypeCategory.INTEGER,
                    raw_vendor_type=raw,
                    precision=p,
                    scale=s,
                    bits=bits,
                    extra={"oracle_negative_scale": s < 0},
                )
            elif p is not None:
                return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, precision=p, scale=s or 0)
            else:
                return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, extra={"oracle_ambiguous_number": True})
        elif "FLOAT" in raw or "BINARY_FLOAT" in raw or "BINARY_DOUBLE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.FLOAT, raw_vendor_type=raw, bits=64)
        elif "NVARCHAR2" in raw or "NCHAR" in raw:
            return CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type=raw, length=l or 255, is_unicode=True)
        elif "VARCHAR2" in raw or "VARCHAR" in raw or "CHAR" in raw:
            cat = CanonicalTypeCategory.CHAR if "CHAR" in raw and "VAR" not in raw else CanonicalTypeCategory.VARCHAR
            return CanonicalType(category=cat, raw_vendor_type=raw, length=l or 255)
        elif "CLOB" in raw or "NCLOB" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TEXT, raw_vendor_type=raw, is_unicode=("NCLOB" in raw))
        elif "BLOB" in raw or "RAW" in raw or "LONG RAW" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BLOB, raw_vendor_type=raw)
        elif "TIMESTAMPTZ" in raw or "WITH TIME ZONE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMPTZ, raw_vendor_type=raw, timezone_aware=True)
        elif "WITH LOCAL TIME ZONE" in raw:
            return CanonicalType(
                category=CanonicalTypeCategory.TIMESTAMPTZ,
                raw_vendor_type=raw,
                timezone_aware=True,
                extra={"oracle_local_tz": True},
            )
        elif "DATE" in raw or "TIMESTAMP" in raw:
            # Oracle DATE contains date + time components!
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMP, raw_vendor_type=raw, timezone_aware=False)
        else:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, length=l, precision=p, scale=s)

    @staticmethod
    def _normalize_postgresql(raw: str, l: Optional[int], p: Optional[int], s: Optional[int]) -> CanonicalType:
        if "BIGINT" in raw or "INT8" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=64)
        elif "INTEGER" in raw or "INT" in raw or "INT4" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=32)
        elif "SMALLINT" in raw or "INT2" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=16)
        elif "NUMERIC" in raw or "DECIMAL" in raw:
            return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, precision=p, scale=s)
        elif "REAL" in raw or "FLOAT" in raw or "DOUBLE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.FLOAT, raw_vendor_type=raw, bits=64)
        elif "BOOL" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif "VARCHAR" in raw or "CHARACTER VARYING" in raw:
            return CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type=raw, length=l or 255)
        elif "TEXT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TEXT, raw_vendor_type=raw)
        elif "BYTEA" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BLOB, raw_vendor_type=raw)
        elif "TIMESTAMPTZ" in raw or "WITH TIME ZONE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMPTZ, raw_vendor_type=raw, timezone_aware=True)
        elif "TIMESTAMP" in raw or "DATE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMP, raw_vendor_type=raw, timezone_aware=False)
        elif "UUID" in raw:
            return CanonicalType(category=CanonicalTypeCategory.UUID, raw_vendor_type=raw)
        elif "JSONB" in raw:
            return CanonicalType(category=CanonicalTypeCategory.JSONB, raw_vendor_type=raw)
        elif "JSON" in raw:
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        elif "XML" in raw:
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        elif "ARRAY" in raw or "[" in raw:
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw)
        else:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, length=l, precision=p, scale=s)

    @staticmethod
    def _normalize_mysql(
        raw: str,
        l: Optional[int],
        p: Optional[int],
        s: Optional[int],
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> CanonicalType:
        is_unsigned = "UNSIGNED" in raw
        extra_meta = extra_metadata or {}

        # P2.3.1 Hardening: Do NOT blindly map TINYINT(1) to BOOLEAN unless explicit boolean evidence is present!
        if ("TINYINT(1)" in raw or (raw.startswith("TINYINT") and l == 1)) and extra_meta.get("is_boolean"):
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw, extra={"mysql_tinyint1": True})
        elif "TINYINT" in raw:
            return CanonicalType(
                category=CanonicalTypeCategory.INTEGER,
                raw_vendor_type=raw,
                bits=8,
                is_signed=not is_unsigned,
                extra={"mysql_tinyint1_ambiguous": (l == 1 or "TINYINT(1)" in raw)},
            )
        elif "BIGINT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=64, is_signed=not is_unsigned)
        elif "INT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=32, is_signed=not is_unsigned)
        elif "DECIMAL" in raw or "NUMERIC" in raw:
            return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, precision=p, scale=s)
        elif "FLOAT" in raw or "DOUBLE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.FLOAT, raw_vendor_type=raw, bits=64)
        elif "VARCHAR" in raw:
            return CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type=raw, length=l or 255)
        elif "TEXT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TEXT, raw_vendor_type=raw)
        elif "BLOB" in raw or "VARBINARY" in raw or "BINARY" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BLOB, raw_vendor_type=raw)
        elif "DATETIME" in raw or "TIMESTAMP" in raw or "DATE" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMP, raw_vendor_type=raw)
        elif "JSON" in raw:
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        elif "ENUM" in raw:
            return CanonicalType(category=CanonicalTypeCategory.ENUM, raw_vendor_type=raw)
        elif "SET" in raw:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, extra={"mysql_set": True})
        else:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, length=l, precision=p, scale=s)

    @staticmethod
    def _normalize_mssql(raw: str, l: Optional[int], p: Optional[int], s: Optional[int]) -> CanonicalType:
        if "ROWVERSION" in raw or (raw == "TIMESTAMP" and "MSSQL" in raw):
            return CanonicalType(
                category=CanonicalTypeCategory.VARBINARY,
                raw_vendor_type=raw,
                length=8,
                extra={"mssql_rowversion": True},
            )
        elif "BIT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif "BIGINT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=64)
        elif "INT" in raw or "SMALLINT" in raw or "TINYINT" in raw:
            bits = 16 if "SMALLINT" in raw else (8 if "TINYINT" in raw else 32)
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=bits)
        elif "DECIMAL" in raw or "NUMERIC" in raw or "MONEY" in raw:
            return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, precision=p, scale=s)
        elif "FLOAT" in raw or "REAL" in raw:
            return CanonicalType(category=CanonicalTypeCategory.FLOAT, raw_vendor_type=raw, bits=64)
        elif "NVARCHAR" in raw or "NCHAR" in raw or "NTEXT" in raw:
            cat = CanonicalTypeCategory.TEXT if "TEXT" in raw else CanonicalTypeCategory.VARCHAR
            return CanonicalType(category=cat, raw_vendor_type=raw, length=l or 255, is_unicode=True)
        elif "VARCHAR" in raw or "CHAR" in raw or "TEXT" in raw:
            cat = CanonicalTypeCategory.TEXT if "TEXT" in raw else CanonicalTypeCategory.VARCHAR
            return CanonicalType(category=cat, raw_vendor_type=raw, length=l or 255)
        elif "VARBINARY" in raw or "IMAGE" in raw or "BINARY" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BLOB, raw_vendor_type=raw)
        elif "DATETIMEOFFSET" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMPTZ, raw_vendor_type=raw, timezone_aware=True)
        elif "DATETIME" in raw or "DATE" in raw or "TIME" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TIMESTAMP, raw_vendor_type=raw)
        elif "UNIQUEIDENTIFIER" in raw:
            return CanonicalType(category=CanonicalTypeCategory.UUID, raw_vendor_type=raw)
        elif "XML" in raw:
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        else:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, length=l, precision=p, scale=s)

    @staticmethod
    def _normalize_db2(raw: str, l: Optional[int], p: Optional[int], s: Optional[int]) -> CanonicalType:
        if "BIGINT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=64)
        elif "INTEGER" in raw or "INT" in raw:
            return CanonicalType(category=CanonicalTypeCategory.INTEGER, raw_vendor_type=raw, bits=32)
        elif "DECIMAL" in raw or "NUMERIC" in raw:
            return CanonicalType(category=CanonicalTypeCategory.DECIMAL, raw_vendor_type=raw, precision=p, scale=s)
        elif "VARCHAR" in raw:
            return CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type=raw, length=l or 255)
        elif "CLOB" in raw:
            return CanonicalType(category=CanonicalTypeCategory.TEXT, raw_vendor_type=raw)
        elif "BLOB" in raw:
            return CanonicalType(category=CanonicalTypeCategory.BLOB, raw_vendor_type=raw)
        else:
            return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, length=l, precision=p, scale=s)

    # ------------------------------------------------------------------
    # Target Emitters with Truthful Conversion Safety
    # ------------------------------------------------------------------
    @staticmethod
    def _emit_postgresql(c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.INTEGER:
            if not c.is_signed and c.bits == 64:
                return TargetTypeEmission(
                    "POSTGRESQL",
                    "NUMERIC(20,0)",
                    ConversionSafety.SAFE,
                    "Unsigned 64-bit integer mapped to NUMERIC(20,0) to prevent 64-bit signed overflow",
                )
            t = "BIGINT" if c.bits == 64 else ("SMALLINT" if c.bits in (8, 16) else "INTEGER")
            safety = ConversionSafety.POTENTIALLY_LOSSY if c.extra.get("mysql_tinyint1_ambiguous") else ConversionSafety.EXACT
            warn = "Ambiguous MySQL TINYINT(1) emitted as SMALLINT to preserve integer semantics" if c.extra.get("mysql_tinyint1_ambiguous") else None
            return TargetTypeEmission("POSTGRESQL", t, safety, warning_message=warn)
        elif cat == CanonicalTypeCategory.DECIMAL:
            t = f"NUMERIC({c.precision},{c.scale})" if c.precision and c.scale is not None else "NUMERIC"
            warn = "Oracle NUMBER without precision/scale emitted as unconstrained NUMERIC" if c.extra.get("oracle_ambiguous_number") else None
            return TargetTypeEmission("POSTGRESQL", t, ConversionSafety.EXACT, warning_message=warn)
        elif cat == CanonicalTypeCategory.FLOAT:
            return TargetTypeEmission("POSTGRESQL", "DOUBLE PRECISION", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission("POSTGRESQL", "BOOLEAN", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.CHAR:
            return TargetTypeEmission("POSTGRESQL", f"CHAR({c.length or 1})", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.VARCHAR:
            return TargetTypeEmission("POSTGRESQL", f"VARCHAR({c.length or 255})", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TEXT:
            return TargetTypeEmission("POSTGRESQL", "TEXT", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.BLOB, CanonicalTypeCategory.BINARY, CanonicalTypeCategory.VARBINARY):
            warn = "MSSQL ROWVERSION mapped to BYTEA; target database cannot automatically generate rowversion tokens" if c.extra.get("mssql_rowversion") else None
            safety = ConversionSafety.VENDOR_SPECIFIC if c.extra.get("mssql_rowversion") else ConversionSafety.EXACT
            return TargetTypeEmission("POSTGRESQL", "BYTEA", safety, warning_message=warn)
        elif cat in (CanonicalTypeCategory.TIMESTAMP, CanonicalTypeCategory.DATE):
            return TargetTypeEmission("POSTGRESQL", "TIMESTAMP", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TIMESTAMPTZ:
            return TargetTypeEmission("POSTGRESQL", "TIMESTAMPTZ", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.UUID:
            return TargetTypeEmission("POSTGRESQL", "UUID", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.JSONB):
            return TargetTypeEmission("POSTGRESQL", "JSONB", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission("POSTGRESQL", "XML", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.ARRAY:
            return TargetTypeEmission("POSTGRESQL", "TEXT[]", ConversionSafety.SAFE)
        elif cat == CanonicalTypeCategory.ENUM:
            return TargetTypeEmission("POSTGRESQL", "VARCHAR(255)", ConversionSafety.SAFE, "ENUM emitted as VARCHAR(255)")
        else:
            return TargetTypeEmission("POSTGRESQL", "TEXT", ConversionSafety.UNSUPPORTED, f"Unknown native type '{c.raw_vendor_type}' mapped to TEXT")

    @staticmethod
    def _emit_oracle(c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.INTEGER:
            t = "NUMBER(19, 0)" if c.bits == 64 else "NUMBER(10, 0)"
            return TargetTypeEmission("ORACLE", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.DECIMAL:
            t = f"NUMBER({c.precision},{c.scale})" if c.precision and c.scale is not None else "NUMBER"
            return TargetTypeEmission("ORACLE", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.FLOAT:
            return TargetTypeEmission("ORACLE", "BINARY_DOUBLE", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission("ORACLE", "NUMBER(1)", ConversionSafety.SAFE, "Emitted NUMBER(1) for boolean")
        elif cat in (CanonicalTypeCategory.VARCHAR, CanonicalTypeCategory.CHAR):
            t = f"NVARCHAR2({c.length or 255})" if c.is_unicode else f"VARCHAR2({c.length or 255})"
            return TargetTypeEmission("ORACLE", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TEXT:
            return TargetTypeEmission("ORACLE", "CLOB", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.BLOB, CanonicalTypeCategory.BINARY, CanonicalTypeCategory.VARBINARY):
            return TargetTypeEmission("ORACLE", "BLOB", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.TIMESTAMP, CanonicalTypeCategory.DATE):
            return TargetTypeEmission("ORACLE", "TIMESTAMP", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TIMESTAMPTZ:
            return TargetTypeEmission("ORACLE", "TIMESTAMP WITH TIME ZONE", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.UUID:
            return TargetTypeEmission("ORACLE", "VARCHAR2(36)", ConversionSafety.SAFE)
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.JSONB):
            return TargetTypeEmission("ORACLE", "CLOB", ConversionSafety.SAFE)
        else:
            return TargetTypeEmission("ORACLE", "VARCHAR2(4000)", ConversionSafety.UNSUPPORTED, f"Mapped unknown type '{c.raw_vendor_type}' to VARCHAR2(4000)")

    @staticmethod
    def _emit_mysql(c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.INTEGER:
            t = "BIGINT" if c.bits == 64 else "INT"
            if not c.is_signed:
                t += " UNSIGNED"
            return TargetTypeEmission("MYSQL", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.DECIMAL:
            t = f"DECIMAL({c.precision},{c.scale})" if c.precision and c.scale is not None else "DECIMAL(18, 4)"
            return TargetTypeEmission("MYSQL", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.FLOAT:
            return TargetTypeEmission("MYSQL", "DOUBLE", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission("MYSQL", "TINYINT(1)", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.VARCHAR:
            return TargetTypeEmission("MYSQL", f"VARCHAR({c.length or 255})", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TEXT:
            return TargetTypeEmission("MYSQL", "LONGTEXT", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.BLOB, CanonicalTypeCategory.BINARY, CanonicalTypeCategory.VARBINARY):
            return TargetTypeEmission("MYSQL", "LONGBLOB", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TIMESTAMPTZ:
            return TargetTypeEmission("MYSQL", "DATETIME", ConversionSafety.POTENTIALLY_LOSSY, "Timezone offset dropped in MySQL DATETIME")
        elif cat in (CanonicalTypeCategory.TIMESTAMP, CanonicalTypeCategory.DATE):
            return TargetTypeEmission("MYSQL", "DATETIME", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.UUID:
            return TargetTypeEmission("MYSQL", "VARCHAR(36)", ConversionSafety.SAFE)
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.JSONB):
            return TargetTypeEmission("MYSQL", "JSON", ConversionSafety.EXACT)
        else:
            return TargetTypeEmission("MYSQL", "LONGTEXT", ConversionSafety.UNSUPPORTED, f"Mapped unknown type '{c.raw_vendor_type}' to LONGTEXT")

    @staticmethod
    def _emit_mssql(c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.INTEGER:
            t = "BIGINT" if c.bits == 64 else ("SMALLINT" if c.bits == 16 else "INT")
            return TargetTypeEmission("MSSQL", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.DECIMAL:
            t = f"DECIMAL({c.precision},{c.scale})" if c.precision and c.scale is not None else "DECIMAL(18, 4)"
            return TargetTypeEmission("MSSQL", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.FLOAT:
            return TargetTypeEmission("MSSQL", "FLOAT", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission("MSSQL", "BIT", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.VARCHAR, CanonicalTypeCategory.CHAR):
            t = f"NVARCHAR({c.length or 255})" if c.is_unicode else f"VARCHAR({c.length or 255})"
            return TargetTypeEmission("MSSQL", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TEXT:
            return TargetTypeEmission("MSSQL", "NVARCHAR(MAX)", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.BLOB, CanonicalTypeCategory.BINARY, CanonicalTypeCategory.VARBINARY):
            return TargetTypeEmission("MSSQL", "VARBINARY(MAX)", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TIMESTAMP or cat == CanonicalTypeCategory.DATE:
            return TargetTypeEmission("MSSQL", "DATETIME2", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TIMESTAMPTZ:
            return TargetTypeEmission("MSSQL", "DATETIMEOFFSET", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.UUID:
            return TargetTypeEmission("MSSQL", "UNIQUEIDENTIFIER", ConversionSafety.EXACT)
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.JSONB):
            return TargetTypeEmission("MSSQL", "NVARCHAR(MAX)", ConversionSafety.SAFE)
        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission("MSSQL", "XML", ConversionSafety.EXACT)
        else:
            return TargetTypeEmission("MSSQL", "NVARCHAR(MAX)", ConversionSafety.UNSUPPORTED, f"Mapped unknown type '{c.raw_vendor_type}' to NVARCHAR(MAX)")

    @staticmethod
    def _emit_db2(c: CanonicalType) -> TargetTypeEmission:
        """Extensibility Hook: IBM DB2 Target Type Emitter."""
        cat = c.category
        if cat == CanonicalTypeCategory.INTEGER:
            t = "BIGINT" if c.bits == 64 else "INTEGER"
            return TargetTypeEmission("IBM_DB2", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.DECIMAL:
            t = f"DECIMAL({c.precision},{c.scale})" if c.precision and c.scale is not None else "DECIMAL(18, 4)"
            return TargetTypeEmission("IBM_DB2", t, ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.VARCHAR:
            return TargetTypeEmission("IBM_DB2", f"VARCHAR({c.length or 255})", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.TEXT:
            return TargetTypeEmission("IBM_DB2", "CLOB", ConversionSafety.EXACT)
        elif cat == CanonicalTypeCategory.BLOB:
            return TargetTypeEmission("IBM_DB2", "BLOB", ConversionSafety.EXACT)
        else:
            return TargetTypeEmission("IBM_DB2", "VARCHAR(4000)", ConversionSafety.UNSUPPORTED, f"Mapped unknown type '{c.raw_vendor_type}' to VARCHAR(4000)")
