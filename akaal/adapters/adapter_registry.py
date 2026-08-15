"""
Akaal — Adapter Registry
=========================
Central lookup for all 17 supported database/storage adapters.
Import and register adapters here. The registry is used by the
connection factory to resolve the correct adapter at runtime.
"""

from akaal.core.models.enums import SystemType

# Lazy imports to avoid circular dependencies
_REGISTRY: dict = {}


import importlib

def _build_registry() -> dict:
    adapters_map = [
        (SystemType.ORACLE, "akaal.adapters.rdbms.oracle_adapter", "OracleAdapter"),
        (SystemType.POSTGRESQL, "akaal.adapters.rdbms.postgresql_adapter", "PostgreSQLAdapter"),
        (SystemType.MYSQL, "akaal.adapters.rdbms.mysql_adapter", "MySQLAdapter"),
        (SystemType.MARIADB, "akaal.adapters.rdbms.mariadb_adapter", "MariaDBAdapter"),
        (SystemType.MSSQL, "akaal.adapters.rdbms.mssql_adapter", "MSSQLAdapter"),
        (SystemType.IBM_DB2, "akaal.adapters.rdbms.ibm_db2_adapter", "IBMDB2Adapter"),
        (SystemType.SQLITE, "akaal.adapters.rdbms.sqlite_adapter", "SQLiteAdapter"),
        (SystemType.SNOWFLAKE, "akaal.adapters.warehouse.snowflake_adapter", "SnowflakeAdapter"),
        (SystemType.BIGQUERY, "akaal.adapters.warehouse.bigquery_adapter", "BigQueryAdapter"),
        (SystemType.REDSHIFT, "akaal.adapters.warehouse.redshift_adapter", "RedshiftAdapter"),
        (SystemType.DATABRICKS, "akaal.adapters.warehouse.databricks_adapter", "DatabricksAdapter"),
        (SystemType.HDFS, "akaal.adapters.warehouse.hdfs_adapter", "HDFSAdapter"),
        (SystemType.MONGODB, "akaal.adapters.nosql.mongodb_adapter", "MongoDBAdapter"),
        (SystemType.CASSANDRA, "akaal.adapters.nosql.cassandra_adapter", "CassandraAdapter"),
        (SystemType.NEO4J, "akaal.adapters.nosql.neo4j_adapter", "Neo4jAdapter"),
        (SystemType.REDIS, "akaal.adapters.nosql.redis_adapter", "RedisAdapter"),
        (SystemType.ELASTICSEARCH, "akaal.adapters.nosql.elasticsearch_adapter", "ElasticsearchAdapter"),
        (SystemType.S3, "akaal.adapters.cloud.s3_adapter", "S3Adapter"),
        (SystemType.GCS, "akaal.adapters.cloud.gcs_adapter", "GCSAdapter"),
        (SystemType.AZURE_BLOB, "akaal.adapters.cloud.azure_blob_adapter", "AzureBlobAdapter"),
    ]

    registry = {}
    for sys_type, module_path, class_name in adapters_map:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            registry[sys_type] = cls
        except Exception:
            pass
    return registry


def get_adapter_class(system_type: SystemType):
    global _REGISTRY
    if not _REGISTRY:
        _REGISTRY = _build_registry()
    adapter_cls = _REGISTRY.get(system_type)
    if adapter_cls is None:
        raise ValueError(f"No adapter registered for system type: {system_type}")
    return adapter_cls


def create_adapter(config) -> "BaseAdapter":
    """Factory: resolve and instantiate the correct adapter from a ConnectionConfig."""
    adapter_cls = get_adapter_class(config.system_type)
    adapter = adapter_cls(config)
    if getattr(config, "enable_connection_pooling", False):
        from akaal.core.connection_pool.pool import PooledAdapter
        return PooledAdapter(adapter)
    return adapter
