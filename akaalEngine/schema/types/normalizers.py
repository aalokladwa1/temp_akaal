"""
akaalEngine.schema.types.normalizers
====================================
28-Provider source datatype normalization engine for Authority #4 Schema.
Translates native vendor type strings + precision/scale/length dimensions into CanonicalType.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Tuple

from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


class ProviderTypeNormalizers:
    """Normalizes raw native provider data types into CanonicalType."""

    @classmethod
    def normalize(
        cls,
        provider: str,
        raw_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        extra_metadata: Optional[Mapping[str, Any]] = None,
    ) -> CanonicalType:
        """Entrypoint for normalizing any of the 28 adopted providers."""
        prov = str(provider).strip().lower()
        raw = str(raw_type).strip().upper()
        meta = extra_metadata or {}

        # Parse inline parameters if not passed explicitly: e.g. VARCHAR(255), NUMERIC(10,2)
        inline_p, inline_s, inline_l = cls._parse_type_params(raw)
        p = precision if precision is not None else inline_p
        s = scale if scale is not None else inline_s
        l = length if length is not None else inline_l

        # Relational
        if prov in ("postgresql", "postgres"):
            return cls._normalize_postgresql(raw, l, p, s, meta)
        elif prov == "oracle":
            return cls._normalize_oracle(raw, l, p, s, meta)
        elif prov in ("mysql", "mariadb"):
            return cls._normalize_mysql(raw, l, p, s, meta)
        elif prov in ("mssql", "sqlserver"):
            return cls._normalize_mssql(raw, l, p, s, meta)
        elif prov in ("ibm_db2", "db2"):
            return cls._normalize_db2(raw, l, p, s, meta)
        elif prov == "sqlite":
            return cls._normalize_sqlite(raw, l, p, s, meta)

        # Warehouse / Lakehouse
        elif prov == "snowflake":
            return cls._normalize_snowflake(raw, l, p, s, meta)
        elif prov == "bigquery":
            return cls._normalize_bigquery(raw, l, p, s, meta)
        elif prov == "redshift":
            return cls._normalize_redshift(raw, l, p, s, meta)
        elif prov == "databricks":
            return cls._normalize_databricks(raw, l, p, s, meta)

        # NoSQL / Specialized
        elif prov == "mongodb":
            return cls._normalize_mongodb(raw, meta)
        elif prov in ("cassandra", "scylladb"):
            return cls._normalize_cassandra(raw, meta)
        elif prov == "neo4j":
            return cls._normalize_neo4j(raw, meta)
        elif prov in ("redis", "keydb"):
            return cls._normalize_redis(raw, meta)
        elif prov in ("elasticsearch", "opensearch"):
            return cls._normalize_elasticsearch(raw, meta)

        # Streaming
        elif prov in ("kafka", "kinesis", "eventhubs", "event_hubs", "pubsub", "pub_sub"):
            return cls._normalize_streaming(raw, meta)

        # Storage / Datasets
        elif prov in ("s3", "gcs", "azureblob", "azure_blob", "minio", "hdfs"):
            return cls._normalize_storage(raw, meta)

        # Generic Fallback
        return CanonicalType(
            category=CanonicalTypeCategory.UNKNOWN,
            raw_vendor_type=raw_type,
            precision=p,
            scale=s,
            length=l,
        )

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
    # 1. PostgreSQL Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_postgresql(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean in ("INT", "INTEGER", "INT4", "SERIAL", "SERIAL4"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=32, is_signed=True)
        elif clean in ("BIGINT", "INT8", "BIGSERIAL", "SERIAL8"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64, is_signed=True)
        elif clean in ("SMALLINT", "INT2", "SMALLSERIAL", "SERIAL2"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=16, is_signed=True)
        elif clean in ("NUMERIC", "DECIMAL"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 38, scale=s or 0)
        elif clean in ("FLOAT4", "REAL"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("FLOAT8", "DOUBLE PRECISION", "FLOAT"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("VARCHAR", "CHARACTER VARYING", "BPCHAR", "CHAR", "CHARACTER"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l, byte_semantics=False)
        elif clean in ("TEXT", "NAME", "CITEXT"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=None, byte_semantics=False)
        elif clean == "BYTEA":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=l)
        elif clean == "BOOLEAN" or clean == "BOOL":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean in ("TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean in ("TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=True)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, extra={"date_only": True})
        elif clean in ("TIME", "TIME WITHOUT TIME ZONE", "TIMETZ", "TIME WITH TIME ZONE"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware="WITH" in clean, extra={"time_only": True})
        elif clean == "INTERVAL":
            return CanonicalType(category=CanonicalTypeCategory.INTERVAL, raw_vendor_type=raw)
        elif clean in ("JSON", "JSONB"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"is_jsonb": clean == "JSONB"})
        elif clean == "XML":
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        elif clean == "UUID":
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=36, extra={"is_uuid": True})
        elif clean in ("GEOMETRY", "GEOGRAPHY"):
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw, srid=meta.get("srid"))
        elif clean == "VECTOR":
            return CanonicalType(category=CanonicalTypeCategory.VECTOR, raw_vendor_type=raw, dimensions=l or meta.get("dimensions"))
        elif clean.endswith("[]") or clean.startswith("_"):
            elem = clean.rstrip("[]").lstrip("_")
            elem_type = cls._normalize_postgresql(elem, None, None, None, {})
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw, array_element_type=elem_type)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, precision=p, scale=s, length=l)

    # ------------------------------------------------------------------
    # 2. Oracle Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_oracle(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean == "NUMBER":
            if p is not None and s is not None and s <= 0:
                bits = 64 if p > 9 else 32
                return CanonicalType(
                    category=CanonicalTypeCategory.EXACT_NUMERIC,
                    raw_vendor_type=raw,
                    precision=p,
                    scale=s,
                    bits=bits,
                    extra={"oracle_negative_scale": s < 0},
                )
            elif p is not None:
                return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p, scale=s or 0)
            else:
                # Oracle unconstrained NUMBER: arbitrary precision/scale up to 38
                return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=38, scale=127, extra={"oracle_unconstrained": True})
        elif clean in ("BINARY_FLOAT", "FLOAT"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean == "BINARY_DOUBLE":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR"):
            byte_sem = bool(meta.get("char_used") == "B" or "BYTE" in raw)
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l or 4000, byte_semantics=byte_sem)
        elif clean in ("CLOB", "NCLOB"):
            return CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type=raw, extra={"lob_type": "CLOB"})
        elif clean in ("BLOB", "BFILE"):
            return CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type=raw, extra={"lob_type": "BLOB"})
        elif clean in ("RAW", "LONG RAW"):
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=l or 2000)
        elif clean == "DATE":
            # Oracle DATE stores year, month, day, hours, minutes, and seconds
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, extra={"oracle_date": True})
        elif clean == "TIMESTAMP":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, precision=p or 6)
        elif "TIMESTAMP" in clean and "TIME ZONE" in clean:
            is_local = "LOCAL" in clean
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=not is_local, precision=p or 6)
        elif clean == "XMLTYPE":
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        elif clean == "SDO_GEOMETRY":
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw, srid=meta.get("srid"))
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, precision=p, scale=s, length=l)

    # ------------------------------------------------------------------
    # 3. MySQL / MariaDB Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_mysql(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        is_unsigned = "UNSIGNED" in raw
        if clean in ("TINYINT", "TINYINT(1)") and (l == 1 or "(1)" in raw or meta.get("treat_tinyint1_as_boolean", True)):
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean in ("TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER"):
            bits = 8 if clean == "TINYINT" else (16 if clean == "SMALLINT" else (24 if clean == "MEDIUMINT" else 32))
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=bits, is_signed=not is_unsigned)
        elif clean == "BIGINT":
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64, is_signed=not is_unsigned)
        elif clean in ("DECIMAL", "DEC", "NUMERIC"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 10, scale=s or 0, is_signed=not is_unsigned)
        elif clean == "FLOAT":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("DOUBLE", "DOUBLE PRECISION", "REAL"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("VARCHAR", "CHAR"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l, byte_semantics=False)
        elif clean in ("TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=None, byte_semantics=False)
        elif clean in ("BLOB", "TINYBLOB", "MEDIUMBLOB", "LONGBLOB"):
            return CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type=raw, extra={"lob_type": "BLOB"})
        elif clean in ("BINARY", "VARBINARY"):
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=l)
        elif clean in ("DATETIME", "TIMESTAMP"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=(clean == "TIMESTAMP"))
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, extra={"date_only": True})
        elif clean == "TIME":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, extra={"time_only": True})
        elif clean == "JSON":
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        elif clean in ("ENUM", "SET"):
            return CanonicalType(category=CanonicalTypeCategory.UDT, raw_vendor_type=raw, extra={"udt_type": clean})
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, precision=p, scale=s, length=l)

    # ------------------------------------------------------------------
    # 4. MSSQL Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_mssql(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean == "BIT":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean == "TINYINT":
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=8, is_signed=False)
        elif clean == "SMALLINT":
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=16, is_signed=True)
        elif clean in ("INT", "INTEGER"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=32, is_signed=True)
        elif clean == "BIGINT":
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64, is_signed=True)
        elif clean in ("DECIMAL", "NUMERIC", "MONEY", "SMALLMONEY"):
            prec = p or (19 if clean == "MONEY" else (10 if clean == "SMALLMONEY" else 18))
            sc = s or (4 if "MONEY" in clean else 0)
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=prec, scale=sc)
        elif clean in ("FLOAT", "REAL"):
            bits = 32 if clean == "REAL" or (p and p <= 24) else 64
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=bits)
        elif clean in ("VARCHAR", "NVARCHAR", "CHAR", "NCHAR"):
            is_max = "MAX" in raw
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=None if is_max else l, extra={"is_max": is_max, "is_unicode": "N" in clean})
        elif clean in ("TEXT", "NTEXT"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=None)
        elif clean in ("VARBINARY", "BINARY", "IMAGE"):
            is_max = "MAX" in raw or clean == "IMAGE"
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=None if is_max else l, extra={"is_max": is_max})
        elif clean in ("DATETIME", "DATETIME2", "SMALLDATETIME"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False, precision=p or (3 if clean == "DATETIME" else 7))
        elif clean == "DATETIMEOFFSET":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=True, precision=p or 7)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"date_only": True})
        elif clean == "TIME":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"time_only": True})
        elif clean == "UNIQUEIDENTIFIER":
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=36, extra={"is_uuid": True})
        elif clean == "XML":
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        elif clean in ("GEOMETRY", "GEOGRAPHY"):
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, precision=p, scale=s, length=l)

    # ------------------------------------------------------------------
    # 5. IBM Db2 Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_db2(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean in ("SMALLINT", "INTEGER", "INT", "BIGINT"):
            bits = 16 if clean == "SMALLINT" else (32 if clean in ("INTEGER", "INT") else 64)
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=bits)
        elif clean in ("DECIMAL", "DEC", "NUMERIC", "DECFLOAT"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 31, scale=s or 0)
        elif clean in ("REAL", "DOUBLE"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32 if clean == "REAL" else 64)
        elif clean in ("VARCHAR", "CHAR", "CLOB", "DBCLOB"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l)
        elif clean == "BLOB":
            return CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type=raw, extra={"lob_type": "BLOB"})
        elif clean in ("DATE", "TIME", "TIMESTAMP"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean == "XML":
            return CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw, precision=p, scale=s, length=l)

    # ------------------------------------------------------------------
    # 6. SQLite Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_sqlite(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.upper()
        if "INT" in clean:
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif "CHAR" in clean or "CLOB" in clean or "TEXT" in clean:
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l)
        elif "BLOB" in clean or not clean:
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif "REAL" in clean or "FLOA" in clean or "DOUB" in clean:
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p, scale=s)

    # ------------------------------------------------------------------
    # 7. Snowflake Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_snowflake(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean in ("NUMBER", "DECIMAL", "NUMERIC", "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "BYTEINT"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 38, scale=s or 0)
        elif clean in ("FLOAT", "FLOAT4", "FLOAT8", "DOUBLE", "DOUBLE PRECISION", "REAL"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("VARCHAR", "CHAR", "CHARACTER", "STRING", "TEXT"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l)
        elif clean == "BOOLEAN":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean == "BINARY":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=l)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"date_only": True})
        elif clean == "TIME":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"time_only": True})
        elif clean in ("TIMESTAMP", "TIMESTAMP_NTZ"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean in ("TIMESTAMP_TZ", "TIMESTAMP_LTZ"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=clean == "TIMESTAMP_TZ")
        elif clean in ("VARIANT", "OBJECT", "ARRAY"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"snowflake_semi_type": clean})
        elif clean in ("GEOGRAPHY", "GEOMETRY"):
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        elif clean == "VECTOR":
            return CanonicalType(category=CanonicalTypeCategory.VECTOR, raw_vendor_type=raw, dimensions=l)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 8. BigQuery Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_bigquery(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.strip()
        if clean in ("INT64", "INTEGER"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("NUMERIC", "DECIMAL"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=38, scale=9)
        elif clean in ("BIGNUMERIC", "BIGDECIMAL"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=76, scale=38)
        elif clean == "FLOAT64":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean == "STRING":
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean == "BYTES":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean in ("BOOL", "BOOLEAN"):
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"date_only": True})
        elif clean == "DATETIME":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean == "TIMESTAMP":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=True)
        elif clean == "TIME":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"time_only": True})
        elif clean == "GEOGRAPHY":
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        elif clean == "JSON":
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        elif clean.startswith("ARRAY"):
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw)
        elif clean.startswith("STRUCT"):
            return CanonicalType(category=CanonicalTypeCategory.UDT, raw_vendor_type=raw, extra={"is_struct": True})
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 9. Redshift Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_redshift(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean in ("SMALLINT", "INT2"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=16)
        elif clean in ("INTEGER", "INT", "INT4"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("BIGINT", "INT8"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("DECIMAL", "NUMERIC"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 18, scale=s or 0)
        elif clean in ("REAL", "FLOAT4"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("DOUBLE PRECISION", "FLOAT8", "FLOAT"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("VARCHAR", "CHARACTER VARYING", "NVARCHAR", "TEXT", "BPCHAR", "CHAR"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=l)
        elif clean == "BOOLEAN" or clean == "BOOL":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean in ("TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean in ("TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True, timezone_offset_preserved=True)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"date_only": True})
        elif clean in ("VARBYTE", "BINARY VARYING"):
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw, length=l)
        elif clean == "SUPER":
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"is_super": True})
        elif clean in ("GEOMETRY", "GEOGRAPHY"):
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 10. Databricks / Spark Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_databricks(cls, raw: str, l: Optional[int], p: Optional[int], s: Optional[int], meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"\(.*?\)", "", raw).strip()
        if clean in ("BYTE", "TINYINT"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=8)
        elif clean in ("SHORT", "SMALLINT"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=16)
        elif clean in ("INT", "INTEGER"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("LONG", "BIGINT"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("DECIMAL", "DEC", "NUMERIC"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=p or 10, scale=s or 0)
        elif clean == "FLOAT":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean == "DOUBLE":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean == "STRING":
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean == "BINARY":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean == "BOOLEAN":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean == "TIMESTAMP":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True)
        elif clean == "TIMESTAMP_NTZ":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=False)
        elif clean == "DATE":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, extra={"date_only": True})
        elif clean.startswith("VARIANT") or clean.startswith("MAP") or clean.startswith("STRUCT") or clean.startswith("ARRAY"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"databricks_complex": clean})
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 11. MongoDB Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_mongodb(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("string", "str"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean in ("int", "int32"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=32)
        elif clean in ("long", "int64"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("double", "float"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("decimal", "decimal128"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=38, scale=12)
        elif clean in ("bool", "boolean"):
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean in ("date", "timestamp"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True)
        elif clean in ("bindata", "binary"):
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean in ("objectid", "oid"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=24, extra={"is_objectid": True})
        elif clean in ("array", "list"):
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw)
        elif clean in ("object", "document"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 12. Cassandra / ScyllaDB Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_cassandra(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = re.sub(r"<.*?>", "", raw).strip().lower()
        if clean in ("int", "smallint", "tinyint", "bigint", "varint"):
            bits = 8 if clean == "tinyint" else (16 if clean == "smallint" else (32 if clean == "int" else 64))
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=bits)
        elif clean == "decimal":
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, precision=38, scale=10)
        elif clean in ("float", "double"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32 if clean == "float" else 64)
        elif clean in ("varchar", "text", "ascii"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean == "blob":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean == "boolean":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean in ("date", "time", "timestamp"):
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=(clean == "timestamp"))
        elif clean in ("uuid", "timeuuid"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw, length=36, extra={"is_uuid": True})
        elif clean in ("list", "set"):
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw)
        elif clean in ("map", "tuple", "frozen"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 13. Neo4j Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_neo4j(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("string", "str"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean in ("integer", "int"):
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean == "float":
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=64)
        elif clean in ("boolean", "bool"):
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif "date" in clean or "time" in clean:
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw)
        elif clean == "point":
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        elif clean in ("list", "map"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 14. Redis / KeyDB Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_redis(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("string", "str"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean in ("hash", "json"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        elif clean in ("list", "set", "zset"):
            return CanonicalType(category=CanonicalTypeCategory.ARRAY, raw_vendor_type=raw)
        elif clean == "stream":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 15. Elasticsearch / OpenSearch Normalizer
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_elasticsearch(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("keyword", "text"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean in ("long", "integer", "short", "byte"):
            bits = 8 if clean == "byte" else (16 if clean == "short" else (32 if clean == "integer" else 64))
            return CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type=raw, bits=bits)
        elif clean in ("double", "float", "half_float", "scaled_float"):
            return CanonicalType(category=CanonicalTypeCategory.APPROX_NUMERIC, raw_vendor_type=raw, bits=32 if "float" in clean else 64)
        elif clean == "boolean":
            return CanonicalType(category=CanonicalTypeCategory.BOOLEAN, raw_vendor_type=raw)
        elif clean == "date":
            return CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type=raw, is_timezone_aware=True)
        elif clean == "binary":
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean in ("geo_point", "geo_shape"):
            return CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type=raw)
        elif clean in ("dense_vector", "knn_vector"):
            return CanonicalType(category=CanonicalTypeCategory.VECTOR, raw_vendor_type=raw, dimensions=meta.get("dims"))
        elif clean in ("nested", "object"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.UNKNOWN, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 16. Streaming Normalizer (Kafka, Kinesis, Event Hubs, Pub/Sub)
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_streaming(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("string", "text"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean in ("bytes", "binary"):
            return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
        elif clean in ("avro", "json", "protobuf", "proto"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"streaming_schema": clean})
        return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)

    # ------------------------------------------------------------------
    # 17. Storage Normalizer (S3, GCS, Azure Blob, MinIO, HDFS)
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_storage(cls, raw: str, meta: Mapping[str, Any]) -> CanonicalType:
        clean = raw.lower()
        if clean in ("parquet", "orc", "avro"):
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw, extra={"storage_format": clean})
        elif clean in ("csv", "tsv", "text"):
            return CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type=raw)
        elif clean == "json":
            return CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type=raw)
        return CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type=raw)
