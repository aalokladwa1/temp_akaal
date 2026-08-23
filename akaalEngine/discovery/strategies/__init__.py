"""
akaalEngine.discovery.strategies
================================
28 concrete physical discovery strategies for Authority #3 Discovery.
"""

from akaalEngine.discovery.strategies.nosql import (
    CassandraDiscoveryStrategy,
    ElasticsearchDiscoveryStrategy,
    KeyDBDiscoveryStrategy,
    MongoDBDiscoveryStrategy,
    Neo4jDiscoveryStrategy,
    OpenSearchDiscoveryStrategy,
    RedisDiscoveryStrategy,
    ScyllaDBDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.relational import (
    IBMDb2DiscoveryStrategy,
    MariaDBDiscoveryStrategy,
    MSSQLDiscoveryStrategy,
    MySQLDiscoveryStrategy,
    OracleDiscoveryStrategy,
    PostgresDiscoveryStrategy,
    SQLiteDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.storage import (
    AzureBlobDiscoveryStrategy,
    GCSDiscoveryStrategy,
    HDFSDiscoveryStrategy,
    MinIODiscoveryStrategy,
    S3DiscoveryStrategy,
)
from akaalEngine.discovery.strategies.streaming import (
    EventHubsDiscoveryStrategy,
    KafkaDiscoveryStrategy,
    KinesisDiscoveryStrategy,
    PubSubDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.warehouse import (
    BigQueryDiscoveryStrategy,
    DatabricksDiscoveryStrategy,
    RedshiftDiscoveryStrategy,
    SnowflakeDiscoveryStrategy,
)

ALL_DISCOVERY_STRATEGIES = [
    # Relational (7)
    SQLiteDiscoveryStrategy,
    PostgresDiscoveryStrategy,
    MySQLDiscoveryStrategy,
    MariaDBDiscoveryStrategy,
    OracleDiscoveryStrategy,
    MSSQLDiscoveryStrategy,
    IBMDb2DiscoveryStrategy,
    # Warehouse (4)
    SnowflakeDiscoveryStrategy,
    BigQueryDiscoveryStrategy,
    RedshiftDiscoveryStrategy,
    DatabricksDiscoveryStrategy,
    # NoSQL & Search (8)
    MongoDBDiscoveryStrategy,
    CassandraDiscoveryStrategy,
    ScyllaDBDiscoveryStrategy,
    Neo4jDiscoveryStrategy,
    RedisDiscoveryStrategy,
    KeyDBDiscoveryStrategy,
    ElasticsearchDiscoveryStrategy,
    OpenSearchDiscoveryStrategy,
    # Streaming (4)
    KafkaDiscoveryStrategy,
    KinesisDiscoveryStrategy,
    EventHubsDiscoveryStrategy,
    PubSubDiscoveryStrategy,
    # Storage (5)
    S3DiscoveryStrategy,
    GCSDiscoveryStrategy,
    AzureBlobDiscoveryStrategy,
    MinIODiscoveryStrategy,
    HDFSDiscoveryStrategy,
]

__all__ = [
    "ALL_DISCOVERY_STRATEGIES",
    # Relational
    "SQLiteDiscoveryStrategy",
    "PostgresDiscoveryStrategy",
    "MySQLDiscoveryStrategy",
    "MariaDBDiscoveryStrategy",
    "OracleDiscoveryStrategy",
    "MSSQLDiscoveryStrategy",
    "IBMDb2DiscoveryStrategy",
    # Warehouse
    "SnowflakeDiscoveryStrategy",
    "BigQueryDiscoveryStrategy",
    "RedshiftDiscoveryStrategy",
    "DatabricksDiscoveryStrategy",
    # NoSQL
    "MongoDBDiscoveryStrategy",
    "CassandraDiscoveryStrategy",
    "ScyllaDBDiscoveryStrategy",
    "Neo4jDiscoveryStrategy",
    "RedisDiscoveryStrategy",
    "KeyDBDiscoveryStrategy",
    "ElasticsearchDiscoveryStrategy",
    "OpenSearchDiscoveryStrategy",
    # Streaming
    "KafkaDiscoveryStrategy",
    "KinesisDiscoveryStrategy",
    "EventHubsDiscoveryStrategy",
    "PubSubDiscoveryStrategy",
    # Storage
    "S3DiscoveryStrategy",
    "GCSDiscoveryStrategy",
    "AzureBlobDiscoveryStrategy",
    "MinIODiscoveryStrategy",
    "HDFSDiscoveryStrategy",
]
