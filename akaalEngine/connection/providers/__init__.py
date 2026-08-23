"""
akaalEngine.connection.providers
================================
Internal provider strategies, SPI contracts, conformance suite, and provider categories.
"""

from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.providers.conformance import (
    ConformanceCheckResult,
    ConformanceReport,
    ProviderConformanceSuite,
)

# Import concrete strategies for convenient catalog population
from akaalEngine.connection.providers.relational import (
    SQLiteProviderStrategy,
    PostgreSQLProviderStrategy,
    MySQLProviderStrategy,
    MariaDBProviderStrategy,
    OracleProviderStrategy,
    MSSQLProviderStrategy,
    IBMDb2ProviderStrategy,
)

from akaalEngine.connection.providers.warehouse import (
    SnowflakeProviderStrategy,
    BigQueryProviderStrategy,
    RedshiftProviderStrategy,
    DatabricksProviderStrategy,
)

from akaalEngine.connection.providers.nosql import (
    MongoDBProviderStrategy,
    CassandraProviderStrategy,
    ScyllaDBProviderStrategy,
    Neo4jProviderStrategy,
    RedisProviderStrategy,
    KeyDBProviderStrategy,
    ElasticsearchProviderStrategy,
    OpenSearchProviderStrategy,
)

from akaalEngine.connection.providers.streaming import (
    KafkaProviderStrategy,
    KinesisProviderStrategy,
    EventHubsProviderStrategy,
    PubSubProviderStrategy,
)

from akaalEngine.connection.providers.storage import (
    S3ProviderStrategy,
    GCSProviderStrategy,
    AzureBlobProviderStrategy,
    MinIOProviderStrategy,
    HDFSProviderStrategy,
)

__all__ = [
    # Base & Conformance
    "BaseProviderStrategy",
    "ConformanceCheckResult",
    "ConformanceReport",
    "ProviderConformanceSuite",
    # Relational
    "SQLiteProviderStrategy",
    "PostgreSQLProviderStrategy",
    "MySQLProviderStrategy",
    "MariaDBProviderStrategy",
    "OracleProviderStrategy",
    "MSSQLProviderStrategy",
    "IBMDb2ProviderStrategy",
    # Warehouse
    "SnowflakeProviderStrategy",
    "BigQueryProviderStrategy",
    "RedshiftProviderStrategy",
    "DatabricksProviderStrategy",
    # NoSQL
    "MongoDBProviderStrategy",
    "CassandraProviderStrategy",
    "ScyllaDBProviderStrategy",
    "Neo4jProviderStrategy",
    "RedisProviderStrategy",
    "KeyDBProviderStrategy",
    "ElasticsearchProviderStrategy",
    "OpenSearchProviderStrategy",
    # Streaming
    "KafkaProviderStrategy",
    "KinesisProviderStrategy",
    "EventHubsProviderStrategy",
    "PubSubProviderStrategy",
    # Storage
    "S3ProviderStrategy",
    "GCSProviderStrategy",
    "AzureBlobProviderStrategy",
    "MinIOProviderStrategy",
    "HDFSProviderStrategy",
]
