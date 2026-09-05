"""
akaalEngine.schema.types.emitters
=================================
Target-native DDL type emission engine for Authority #4 Schema.
Translates CanonicalType into target-native DDL datatype strings with safety classification.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from akaalEngine.schema.models.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)


class ProviderTypeEmitters:
    """Emits target-native DDL datatypes from CanonicalType."""

    @classmethod
    def emit(cls, target_provider: str, ctype: CanonicalType) -> TargetTypeEmission:
        """Entrypoint for emitting target DDL datatype."""
        tgt = str(target_provider).strip().lower()

        # Relational Targets
        if tgt in ("postgresql", "postgres", "cockroachdb", "yugabytedb"):
            return cls._emit_postgresql(ctype)
        elif tgt == "oracle":
            return cls._emit_oracle(ctype)
        elif tgt in ("mysql", "mariadb", "tidb", "singlestore"):
            return cls._emit_mysql(ctype)
        elif tgt in ("mssql", "sqlserver"):
            return cls._emit_mssql(ctype)
        elif tgt in ("ibm_db2", "db2"):
            return cls._emit_db2(ctype)
        elif tgt == "sqlite":
            return cls._emit_sqlite(ctype)

        # Warehouse Targets
        elif tgt == "snowflake":
            return cls._emit_snowflake(ctype)
        elif tgt == "bigquery":
            return cls._emit_bigquery(ctype)
        elif tgt == "redshift":
            return cls._emit_redshift(ctype)
        elif tgt == "databricks":
            return cls._emit_databricks(ctype)
        elif tgt == "clickhouse":
            return cls._emit_clickhouse(ctype)

        # CQL Targets
        elif tgt in ("cassandra", "scylladb"):
            return cls._emit_cql(ctype)

        # Non-relational / Structural Targets
        elif tgt in ("mongodb", "elasticsearch", "opensearch", "kafka", "kinesis", "eventhubs", "event_hubs", "pubsub", "pub_sub", "rabbitmq", "pulsar", "dynamodb", "couchbase", "influxdb", "s3", "gcs", "azureblob", "azure_blob", "minio", "hdfs", "redis", "keydb", "neo4j"):
            return TargetTypeEmission(
                target_engine=target_provider,
                target_native_type="STRUCTURAL_ONLY",
                safety=ConversionSafety.SEMANTICALLY_EQUIVALENT,
                warning_message=f"Target engine '{target_provider}' uses structural schema contracts rather than relational DDL types",
            )

        return TargetTypeEmission(
            target_engine=target_provider,
            target_native_type="TEXT",
            safety=ConversionSafety.UNSUPPORTED,
            warning_message=f"Unsupported target engine: {target_provider}",
        )

    # ------------------------------------------------------------------
    # 1. PostgreSQL Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_postgresql(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.extra.get("oracle_unconstrained"):
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="NUMERIC", safety=ConversionSafety.EXACT)
            elif c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 1000)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type=f"NUMERIC({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="SMALLINT")
            elif c.bits == 64:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="BIGINT")
            elif c.precision is not None and c.precision > 18:
                p = min(c.precision, 1000)
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type=f"NUMERIC({p},0)", extra={"target_precision": p, "target_scale": 0})
            elif c.precision is not None and c.precision > 9:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="BIGINT")
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="INTEGER")

        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="REAL")
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="DOUBLE PRECISION")

        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.extra.get("is_uuid"):
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="UUID")
            if c.length is not None and c.length <= 10485760:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type=f"VARCHAR({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TEXT")

        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="BYTEA")

        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="BOOLEAN")

        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="DATE")
            elif c.extra.get("time_only"):
                if c.is_timezone_aware:
                    return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TIME WITH TIME ZONE", extra={"target_timezone_aware": True})
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TIME WITHOUT TIME ZONE")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TIMESTAMPTZ", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TIMESTAMP WITHOUT TIME ZONE")

        elif cat == CanonicalTypeCategory.INTERVAL:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="INTERVAL")

        elif cat == CanonicalTypeCategory.JSON:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="JSONB")

        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="XML")

        elif cat == CanonicalTypeCategory.LOB:
            if c.extra.get("lob_type") == "CLOB":
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TEXT")
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="BYTEA")

        elif cat == CanonicalTypeCategory.SPATIAL:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="GEOMETRY", requires_compat_helper="postgis")

        elif cat == CanonicalTypeCategory.VECTOR:
            dims = c.dimensions or 1536
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type=f"VECTOR({dims})", requires_compat_helper="pgvector")

        elif cat == CanonicalTypeCategory.ARRAY:
            if c.array_element_type:
                inner = cls._emit_postgresql(c.array_element_type)
                return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type=f"{inner.target_native_type}[]", safety=inner.safety)
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TEXT[]")

        elif cat == CanonicalTypeCategory.UDT:
            return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TEXT", safety=ConversionSafety.COMPATIBLE_WITH_TRANSFORMATION, warning_message="UDT converted to TEXT on target")

        return TargetTypeEmission(target_engine="POSTGRESQL", target_native_type="TEXT", safety=ConversionSafety.UNSUPPORTED)

    # ------------------------------------------------------------------
    # 2. Oracle Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_oracle(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None:
                p = min(c.precision, 38)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="ORACLE", target_native_type=f"NUMBER({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.precision is not None:
                p = min(c.precision, 38)
                return TargetTypeEmission(target_engine="ORACLE", target_native_type=f"NUMBER({p})", extra={"target_precision": p, "target_scale": 0})
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="NUMBER(38)")

        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="ORACLE", target_native_type="BINARY_FLOAT")
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="BINARY_DOUBLE")

        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.length is not None and c.length <= 4000:
                return TargetTypeEmission(target_engine="ORACLE", target_native_type=f"VARCHAR2({c.length} CHAR)", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="CLOB")

        elif cat == CanonicalTypeCategory.BINARY:
            if c.length is not None and c.length <= 2000:
                return TargetTypeEmission(target_engine="ORACLE", target_native_type=f"RAW({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="BLOB")

        elif cat == CanonicalTypeCategory.BOOLEAN:
            # Oracle 23c has BOOLEAN; earlier versions use NUMBER(1)
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="NUMBER(1)", safety=ConversionSafety.SEMANTICALLY_EQUIVALENT)

        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only") or c.extra.get("oracle_date"):
                return TargetTypeEmission(target_engine="ORACLE", target_native_type="DATE")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="ORACLE", target_native_type="TIMESTAMP WITH TIME ZONE", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="TIMESTAMP")

        elif cat == CanonicalTypeCategory.JSON:
            # Oracle 21c+ has native JSON, 19c uses CLOB with IS JSON check constraint
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="CLOB", safety=ConversionSafety.SEMANTICALLY_EQUIVALENT, extra={"is_json_clob": True})

        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="XMLTYPE")

        elif cat == CanonicalTypeCategory.LOB:
            if c.extra.get("lob_type") == "CLOB":
                return TargetTypeEmission(target_engine="ORACLE", target_native_type="CLOB")
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="BLOB")

        elif cat == CanonicalTypeCategory.SPATIAL:
            return TargetTypeEmission(target_engine="ORACLE", target_native_type="SDO_GEOMETRY")

        return TargetTypeEmission(target_engine="ORACLE", target_native_type="VARCHAR2(4000 CHAR)", safety=ConversionSafety.UNSUPPORTED)

    # ------------------------------------------------------------------
    # 3. MySQL / MariaDB Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_mysql(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 65)
                s = min(c.scale, 30)
                return TargetTypeEmission(target_engine="MYSQL", target_native_type=f"DECIMAL({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 8:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="TINYINT")
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="SMALLINT")
            elif c.bits == 64 or (c.precision and c.precision > 9):
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="BIGINT")
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="INT")

        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="FLOAT")
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="DOUBLE")

        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.length is not None and c.length <= 16383:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type=f"VARCHAR({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="LONGTEXT")

        elif cat == CanonicalTypeCategory.BINARY:
            if c.length is not None and c.length <= 65535:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type=f"VARBINARY({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="LONGBLOB")

        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="TINYINT(1)")

        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="DATE")
            elif c.extra.get("time_only"):
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="TIME")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="TIMESTAMP", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="DATETIME")

        elif cat == CanonicalTypeCategory.JSON:
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="JSON")

        elif cat == CanonicalTypeCategory.LOB:
            if c.extra.get("lob_type") == "CLOB":
                return TargetTypeEmission(target_engine="MYSQL", target_native_type="LONGTEXT")
            return TargetTypeEmission(target_engine="MYSQL", target_native_type="LONGBLOB")

        return TargetTypeEmission(target_engine="MYSQL", target_native_type="TEXT", safety=ConversionSafety.UNSUPPORTED)

    # ------------------------------------------------------------------
    # 4. MSSQL Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_mssql(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 38)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="MSSQL", target_native_type=f"DECIMAL({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 8:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="TINYINT")
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="SMALLINT")
            elif c.bits == 64 or (c.precision and c.precision > 9):
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="BIGINT")
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="INT")

        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="REAL")
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="FLOAT")

        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.extra.get("is_uuid"):
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="UNIQUEIDENTIFIER")
            if c.length is not None and c.length <= 4000:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type=f"NVARCHAR({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="NVARCHAR(MAX)")

        elif cat == CanonicalTypeCategory.BINARY:
            if c.length is not None and c.length <= 8000:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type=f"VARBINARY({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="VARBINARY(MAX)")

        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="BIT")

        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="DATE")
            elif c.extra.get("time_only"):
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="TIME")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="DATETIMEOFFSET", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="DATETIME2")

        elif cat == CanonicalTypeCategory.JSON:
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="NVARCHAR(MAX)", safety=ConversionSafety.SEMANTICALLY_EQUIVALENT)

        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="XML")

        elif cat == CanonicalTypeCategory.LOB:
            if c.extra.get("lob_type") == "CLOB":
                return TargetTypeEmission(target_engine="MSSQL", target_native_type="NVARCHAR(MAX)")
            return TargetTypeEmission(target_engine="MSSQL", target_native_type="VARBINARY(MAX)")

        return TargetTypeEmission(target_engine="MSSQL", target_native_type="NVARCHAR(MAX)", safety=ConversionSafety.UNSUPPORTED)

    # ------------------------------------------------------------------
    # 5. IBM Db2 Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_db2(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 31)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="IBM_DB2", target_native_type=f"DECIMAL({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="SMALLINT")
            elif c.bits == 64:
                return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="BIGINT")
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="INTEGER")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="DOUBLE")
        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.length is not None and c.length <= 32672:
                return TargetTypeEmission(target_engine="IBM_DB2", target_native_type=f"VARCHAR({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="CLOB")
        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="BLOB")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="DATE")
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="TIMESTAMP")
        elif cat == CanonicalTypeCategory.XML:
            return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="XML")
        return TargetTypeEmission(target_engine="IBM_DB2", target_native_type="VARCHAR(32672)", safety=ConversionSafety.UNSUPPORTED)

    # ------------------------------------------------------------------
    # 6. SQLite Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_sqlite(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="INTEGER")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="REAL")
        elif cat == CanonicalTypeCategory.CHARACTER:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="TEXT")
        elif cat == CanonicalTypeCategory.BINARY or cat == CanonicalTypeCategory.LOB:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="BLOB")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="INTEGER")
        elif cat == CanonicalTypeCategory.DATETIME:
            return TargetTypeEmission(target_engine="SQLITE", target_native_type="TEXT")
        return TargetTypeEmission(target_engine="SQLITE", target_native_type="TEXT")

    # ------------------------------------------------------------------
    # 7. Snowflake Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_snowflake(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None:
                p = min(c.precision, 38)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type=f"NUMBER({p},{s})", extra={"target_precision": p, "target_scale": s})
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="NUMBER(38,0)")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="FLOAT")
        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.length is not None and c.length <= 16777216:
                return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type=f"VARCHAR({c.length})", extra={"target_length": c.length})
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="VARCHAR")
        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="BINARY")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="BOOLEAN")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="DATE")
            elif c.extra.get("time_only"):
                return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="TIME")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="TIMESTAMP_TZ", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="TIMESTAMP_NTZ")
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.XML, CanonicalTypeCategory.ARRAY, CanonicalTypeCategory.UDT):
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="VARIANT")
        elif cat == CanonicalTypeCategory.SPATIAL:
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="GEOGRAPHY")
        elif cat == CanonicalTypeCategory.VECTOR:
            dims = c.dimensions or 1536
            return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type=f"VECTOR(FLOAT, {dims})")
        return TargetTypeEmission(target_engine="SNOWFLAKE", target_native_type="VARCHAR")

    # ------------------------------------------------------------------
    # 8. BigQuery Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_bigquery(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.scale is not None and c.scale > 9:
                return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="BIGNUMERIC")
            elif c.precision is not None and c.precision > 18:
                return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="NUMERIC")
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="INT64")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="FLOAT64")
        elif cat == CanonicalTypeCategory.CHARACTER:
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="STRING")
        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="BYTES")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="BOOL")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="DATE")
            elif c.extra.get("time_only"):
                return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="TIME")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="TIMESTAMP", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="DATETIME")
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.XML):
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="JSON")
        elif cat == CanonicalTypeCategory.SPATIAL:
            return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="GEOGRAPHY")
        return TargetTypeEmission(target_engine="BIGQUERY", target_native_type="STRING")

    # ------------------------------------------------------------------
    # 9. Redshift Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_redshift(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 38)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type=f"DECIMAL({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="SMALLINT")
            elif c.bits == 64 or (c.precision and c.precision > 9):
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="BIGINT")
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="INTEGER")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="REAL")
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="DOUBLE PRECISION")
        elif cat == CanonicalTypeCategory.CHARACTER:
            length = min(c.length or 65535, 65535)
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type=f"VARCHAR({length})", extra={"target_length": length})
        elif cat == CanonicalTypeCategory.BINARY:
            length = min(c.length or 65535, 65535)
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type=f"VARBYTE({length})", extra={"target_length": length})
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="BOOLEAN")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="DATE")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="TIMESTAMPTZ", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="TIMESTAMP")
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.XML, CanonicalTypeCategory.ARRAY):
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="SUPER")
        elif cat == CanonicalTypeCategory.SPATIAL:
            return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="GEOMETRY")
        return TargetTypeEmission(target_engine="REDSHIFT", target_native_type="VARCHAR(65535)")

    # ------------------------------------------------------------------
    # 10. Databricks / Spark Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_databricks(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 38)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type=f"DECIMAL({p},{s})", extra={"target_precision": p, "target_scale": s})
            elif c.bits == 8:
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="BYTE")
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="SHORT")
            elif c.bits == 64:
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="LONG")
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="INT")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="FLOAT")
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="DOUBLE")
        elif cat == CanonicalTypeCategory.CHARACTER:
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="STRING")
        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="BINARY")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="BOOLEAN")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="DATE")
            elif c.is_timezone_aware:
                return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="TIMESTAMP", extra={"target_timezone_aware": True})
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="TIMESTAMP_NTZ")
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.XML):
            return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="VARIANT")
        return TargetTypeEmission(target_engine="DATABRICKS", target_native_type="STRING")

    # ------------------------------------------------------------------
    # ClickHouse Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_clickhouse(cls, c: CanonicalType) -> TargetTypeEmission:
        nullable = bool(c.extra.get("nullable"))

        def _wrap(native: str) -> str:
            return f"Nullable({native})" if nullable else native

        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.precision is not None and c.scale is not None and c.scale > 0:
                p = min(c.precision, 76)
                s = min(c.scale, p)
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap(f"Decimal({p},{s})"), extra={"target_precision": p, "target_scale": s})
            signed = c.is_signed
            if c.bits == 8:
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Int8" if signed else "UInt8"))
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Int16" if signed else "UInt16"))
            elif c.bits == 64:
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Int64" if signed else "UInt64"))
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Int32" if signed else "UInt32"))
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Float32"))
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Float64"))
        elif cat == CanonicalTypeCategory.CHARACTER:
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("String"))
        elif cat == CanonicalTypeCategory.BINARY:
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("String"), warning_message="ClickHouse has no dedicated binary type; String is used as a byte-string container.")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Bool"))
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("Date"))
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("DateTime64(3)"))
        elif cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.XML):
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type="String", safety=ConversionSafety.LOSSY, warning_message="Structured JSON/XML is flattened to a String column in ClickHouse without a dedicated JSON column type enabled.")
        elif cat == CanonicalTypeCategory.ARRAY:
            return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type="Array(String)", safety=ConversionSafety.COMPATIBLE_WITH_TRANSFORMATION)
        return TargetTypeEmission(target_engine="CLICKHOUSE", target_native_type=_wrap("String"))

    # ------------------------------------------------------------------
    # 11. Cassandra / ScyllaDB (CQL) Emitter
    # ------------------------------------------------------------------
    @classmethod
    def _emit_cql(cls, c: CanonicalType) -> TargetTypeEmission:
        cat = c.category
        if cat == CanonicalTypeCategory.EXACT_NUMERIC:
            if c.scale is not None and c.scale > 0:
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="decimal")
            elif c.bits == 8:
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="tinyint")
            elif c.bits == 16:
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="smallint")
            elif c.bits == 64:
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="bigint")
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="int")
        elif cat == CanonicalTypeCategory.APPROX_NUMERIC:
            if c.bits == 32:
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="float")
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="double")
        elif cat == CanonicalTypeCategory.CHARACTER:
            if c.extra.get("is_uuid"):
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="uuid")
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="text")
        elif cat == CanonicalTypeCategory.BINARY or cat == CanonicalTypeCategory.LOB:
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="blob")
        elif cat == CanonicalTypeCategory.BOOLEAN:
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="boolean")
        elif cat == CanonicalTypeCategory.DATETIME:
            if c.extra.get("date_only"):
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="date")
            elif c.extra.get("time_only"):
                return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="time")
            return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="timestamp")
        return TargetTypeEmission(target_engine="CASSANDRA", target_native_type="text")
