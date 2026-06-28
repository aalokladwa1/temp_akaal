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


def _build_registry() -> dict:
    from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
    from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
    from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
    from akaal.adapters.rdbms.mariadb_adapter import MariaDBAdapter
    from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter
    from akaal.adapters.rdbms.ibm_db2_adapter import IBMDB2Adapter
    from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter
    from akaal.adapters.warehouse.snowflake_adapter import SnowflakeAdapter
    from akaal.adapters.warehouse.bigquery_adapter import BigQueryAdapter
    from akaal.adapters.warehouse.redshift_adapter import RedshiftAdapter
    from akaal.adapters.warehouse.hdfs_adapter import HDFSAdapter
    from akaal.adapters.nosql.mongodb_adapter import MongoDBAdapter
    from akaal.adapters.nosql.cassandra_adapter import CassandraAdapter
    from akaal.adapters.nosql.neo4j_adapter import Neo4jAdapter
    from akaal.adapters.nosql.redis_adapter import RedisAdapter
    from akaal.adapters.nosql.elasticsearch_adapter import ElasticsearchAdapter
    from akaal.adapters.cloud.s3_adapter import S3Adapter
    from akaal.adapters.cloud.gcs_adapter import GCSAdapter
    from akaal.adapters.cloud.azure_blob_adapter import AzureBlobAdapter

    return {
        SystemType.ORACLE:         OracleAdapter,
        SystemType.POSTGRESQL:     PostgreSQLAdapter,
        SystemType.MYSQL:          MySQLAdapter,
        SystemType.MARIADB:        MariaDBAdapter,
        SystemType.MSSQL:          MSSQLAdapter,
        SystemType.IBM_DB2:        IBMDB2Adapter,
        SystemType.SQLITE:         SQLiteAdapter,
        SystemType.SNOWFLAKE:      SnowflakeAdapter,
        SystemType.BIGQUERY:       BigQueryAdapter,
        SystemType.REDSHIFT:       RedshiftAdapter,
        SystemType.HDFS:           HDFSAdapter,
        SystemType.MONGODB:        MongoDBAdapter,
        SystemType.CASSANDRA:      CassandraAdapter,
        SystemType.NEO4J:          Neo4jAdapter,
        SystemType.REDIS:          RedisAdapter,
        SystemType.ELASTICSEARCH:  ElasticsearchAdapter,
        SystemType.S3:             S3Adapter,
        SystemType.GCS:            GCSAdapter,
        SystemType.AZURE_BLOB:     AzureBlobAdapter,
    }


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
    return adapter_cls(config)
