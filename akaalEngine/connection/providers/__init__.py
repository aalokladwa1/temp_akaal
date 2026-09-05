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
    CockroachDBProviderStrategy,
    YugabyteDBProviderStrategy,
    TiDBProviderStrategy,
    SingleStoreProviderStrategy,
)

from akaalEngine.connection.providers.warehouse import (
    SnowflakeProviderStrategy,
    BigQueryProviderStrategy,
    RedshiftProviderStrategy,
    DatabricksProviderStrategy,
    ClickHouseProviderStrategy,
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
    DynamoDBProviderStrategy,
    CouchbaseProviderStrategy,
)

from akaalEngine.connection.providers.streaming import (
    KafkaProviderStrategy,
    KinesisProviderStrategy,
    EventHubsProviderStrategy,
    PubSubProviderStrategy,
    RabbitMQProviderStrategy,
    PulsarProviderStrategy,
)

from akaalEngine.connection.providers.storage import (
    S3ProviderStrategy,
    GCSProviderStrategy,
    AzureBlobProviderStrategy,
    MinIOProviderStrategy,
    HDFSProviderStrategy,
)

from akaalEngine.connection.providers.timeseries import (
    InfluxDBProviderStrategy,
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
    "CockroachDBProviderStrategy",
    "YugabyteDBProviderStrategy",
    "TiDBProviderStrategy",
    "SingleStoreProviderStrategy",
    # Warehouse
    "SnowflakeProviderStrategy",
    "BigQueryProviderStrategy",
    "RedshiftProviderStrategy",
    "DatabricksProviderStrategy",
    "ClickHouseProviderStrategy",
    # NoSQL
    "MongoDBProviderStrategy",
    "CassandraProviderStrategy",
    "ScyllaDBProviderStrategy",
    "Neo4jProviderStrategy",
    "RedisProviderStrategy",
    "KeyDBProviderStrategy",
    "ElasticsearchProviderStrategy",
    "OpenSearchProviderStrategy",
    "DynamoDBProviderStrategy",
    "CouchbaseProviderStrategy",
    # Streaming
    "KafkaProviderStrategy",
    "KinesisProviderStrategy",
    "EventHubsProviderStrategy",
    "PubSubProviderStrategy",
    "RabbitMQProviderStrategy",
    "PulsarProviderStrategy",
    # Storage
    "S3ProviderStrategy",
    "GCSProviderStrategy",
    "AzureBlobProviderStrategy",
    "MinIOProviderStrategy",
    "HDFSProviderStrategy",
    # Time-series
    "InfluxDBProviderStrategy",
]
