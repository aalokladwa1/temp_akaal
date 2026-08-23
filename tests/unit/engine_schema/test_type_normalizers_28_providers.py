"""
tests.unit.engine_schema.test_type_normalizers_28_providers
===========================================================
Unit tests proving source datatype normalization across all 28 adopted providers (SCH-015, SCH-016).
"""

import pytest

from akaalEngine.schema.models.types import CanonicalTypeCategory
from akaalEngine.schema.types.normalizers import ProviderTypeNormalizers
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


def test_relational_providers_normalization():
    # 1. PostgreSQL
    pg_num = CanonicalTypeRegistry.normalize_source_type("postgresql", "NUMERIC(12,4)")
    assert pg_num.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert pg_num.precision == 12
    assert pg_num.scale == 4

    pg_jsonb = CanonicalTypeRegistry.normalize_source_type("postgresql", "JSONB")
    assert pg_jsonb.category == CanonicalTypeCategory.JSON

    pg_vec = CanonicalTypeRegistry.normalize_source_type("postgresql", "VECTOR", length=1536)
    assert pg_vec.category == CanonicalTypeCategory.VECTOR
    assert pg_vec.dimensions == 1536

    # 2. Oracle
    ora_num = CanonicalTypeRegistry.normalize_source_type("oracle", "NUMBER(10,2)")
    assert ora_num.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert ora_num.precision == 10
    assert ora_num.scale == 2

    ora_unconstrained = CanonicalTypeRegistry.normalize_source_type("oracle", "NUMBER")
    assert ora_unconstrained.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert ora_unconstrained.extra.get("oracle_unconstrained") is True

    ora_blob = CanonicalTypeRegistry.normalize_source_type("oracle", "BLOB")
    assert ora_blob.category == CanonicalTypeCategory.LOB

    # 3. MySQL
    my_dec = CanonicalTypeRegistry.normalize_source_type("mysql", "DECIMAL(8,2)")
    assert my_dec.category == CanonicalTypeCategory.EXACT_NUMERIC

    my_bool = CanonicalTypeRegistry.normalize_source_type("mysql", "TINYINT(1)")
    assert my_bool.category == CanonicalTypeCategory.BOOLEAN

    # 4. MariaDB
    maria_uuid = CanonicalTypeRegistry.normalize_source_type("mariadb", "VARCHAR(36)")
    assert maria_uuid.category == CanonicalTypeCategory.CHARACTER

    # 5. MSSQL
    ms_dt = CanonicalTypeRegistry.normalize_source_type("mssql", "DATETIMEOFFSET")
    assert ms_dt.category == CanonicalTypeCategory.DATETIME
    assert ms_dt.is_timezone_aware is True

    ms_bit = CanonicalTypeRegistry.normalize_source_type("mssql", "BIT")
    assert ms_bit.category == CanonicalTypeCategory.BOOLEAN

    # 6. IBM Db2
    db2_dec = CanonicalTypeRegistry.normalize_source_type("ibm_db2", "DECFLOAT")
    assert db2_dec.category == CanonicalTypeCategory.EXACT_NUMERIC

    # 7. SQLite
    sqlite_txt = CanonicalTypeRegistry.normalize_source_type("sqlite", "TEXT")
    assert sqlite_txt.category == CanonicalTypeCategory.CHARACTER


def test_warehouse_providers_normalization():
    # 8. Snowflake
    sf_num = CanonicalTypeRegistry.normalize_source_type("snowflake", "NUMBER(38,0)")
    assert sf_num.category == CanonicalTypeCategory.EXACT_NUMERIC

    sf_variant = CanonicalTypeRegistry.normalize_source_type("snowflake", "VARIANT")
    assert sf_variant.category == CanonicalTypeCategory.JSON

    # 9. BigQuery
    bq_int = CanonicalTypeRegistry.normalize_source_type("bigquery", "INT64")
    assert bq_int.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert bq_int.bits == 64

    bq_bignum = CanonicalTypeRegistry.normalize_source_type("bigquery", "BIGNUMERIC")
    assert bq_bignum.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert bq_bignum.precision == 76

    # 10. Redshift
    rs_super = CanonicalTypeRegistry.normalize_source_type("redshift", "SUPER")
    assert rs_super.category == CanonicalTypeCategory.JSON

    # 11. Databricks
    db_struct = CanonicalTypeRegistry.normalize_source_type("databricks", "STRUCT<a:INT>")
    assert db_struct.category == CanonicalTypeCategory.JSON


def test_nosql_providers_normalization():
    # 12. MongoDB
    mongo_oid = CanonicalTypeRegistry.normalize_source_type("mongodb", "objectId")
    assert mongo_oid.category == CanonicalTypeCategory.CHARACTER
    assert mongo_oid.extra.get("is_objectid") is True

    # 13. Cassandra
    cas_uuid = CanonicalTypeRegistry.normalize_source_type("cassandra", "timeuuid")
    assert cas_uuid.category == CanonicalTypeCategory.CHARACTER

    # 14. ScyllaDB
    scylla_dec = CanonicalTypeRegistry.normalize_source_type("scylladb", "decimal")
    assert scylla_dec.category == CanonicalTypeCategory.EXACT_NUMERIC

    # 15. Neo4j
    neo_point = CanonicalTypeRegistry.normalize_source_type("neo4j", "Point")
    assert neo_point.category == CanonicalTypeCategory.SPATIAL

    # 16. Redis
    redis_hash = CanonicalTypeRegistry.normalize_source_type("redis", "hash")
    assert redis_hash.category == CanonicalTypeCategory.JSON

    # 17. KeyDB
    keydb_zset = CanonicalTypeRegistry.normalize_source_type("keydb", "zset")
    assert keydb_zset.category == CanonicalTypeCategory.ARRAY

    # 18. Elasticsearch
    es_geo = CanonicalTypeRegistry.normalize_source_type("elasticsearch", "geo_point")
    assert es_geo.category == CanonicalTypeCategory.SPATIAL

    es_vec = CanonicalTypeRegistry.normalize_source_type("elasticsearch", "dense_vector", extra_metadata={"dims": 768})
    assert es_vec.category == CanonicalTypeCategory.VECTOR
    assert es_vec.dimensions == 768

    # 19. OpenSearch
    os_knn = CanonicalTypeRegistry.normalize_source_type("opensearch", "knn_vector", extra_metadata={"dims": 1024})
    assert os_knn.category == CanonicalTypeCategory.VECTOR


def test_streaming_and_storage_providers_normalization():
    # 20. Kafka
    kafka_avro = CanonicalTypeRegistry.normalize_source_type("kafka", "avro")
    assert kafka_avro.category == CanonicalTypeCategory.JSON

    # 21. Kinesis
    kin_bytes = CanonicalTypeRegistry.normalize_source_type("kinesis", "bytes")
    assert kin_bytes.category == CanonicalTypeCategory.BINARY

    # 22. Event Hubs
    eh_json = CanonicalTypeRegistry.normalize_source_type("event_hubs", "json")
    assert eh_json.category == CanonicalTypeCategory.JSON

    # 23. Pub/Sub
    ps_proto = CanonicalTypeRegistry.normalize_source_type("pubsub", "proto")
    assert ps_proto.category == CanonicalTypeCategory.JSON

    # 24. S3
    s3_parq = CanonicalTypeRegistry.normalize_source_type("s3", "parquet")
    assert s3_parq.category == CanonicalTypeCategory.JSON

    # 25. GCS
    gcs_orc = CanonicalTypeRegistry.normalize_source_type("gcs", "orc")
    assert gcs_orc.category == CanonicalTypeCategory.JSON

    # 26. Azure Blob
    az_csv = CanonicalTypeRegistry.normalize_source_type("azure_blob", "csv")
    assert az_csv.category == CanonicalTypeCategory.CHARACTER

    # 27. MinIO
    minio_json = CanonicalTypeRegistry.normalize_source_type("minio", "json")
    assert minio_json.category == CanonicalTypeCategory.JSON

    # 28. HDFS
    hdfs_seq = CanonicalTypeRegistry.normalize_source_type("hdfs", "sequencefile")
    assert hdfs_seq.category == CanonicalTypeCategory.BINARY
