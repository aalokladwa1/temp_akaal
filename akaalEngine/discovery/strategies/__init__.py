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
    DynamoDBDiscoveryStrategy,
    CouchbaseDiscoveryStrategy,
    CosmosDBDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.relational import (
    IBMDb2DiscoveryStrategy,
    MariaDBDiscoveryStrategy,
    MSSQLDiscoveryStrategy,
    MySQLDiscoveryStrategy,
    OracleDiscoveryStrategy,
    PostgresDiscoveryStrategy,
    SQLiteDiscoveryStrategy,
    CockroachDBDiscoveryStrategy,
    YugabyteDBDiscoveryStrategy,
    TiDBDiscoveryStrategy,
    SingleStoreDiscoveryStrategy,
    TeradataDiscoveryStrategy,
    VerticaDiscoveryStrategy,
    SAPHANADiscoveryStrategy,
    SAPASEDiscoveryStrategy,
    InformixDiscoveryStrategy,
    SpannerDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.application import (
    SalesforceDiscoveryStrategy,
    ServiceNowDiscoveryStrategy,
    SAPApplicationDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.storage import (
    AzureBlobDiscoveryStrategy,
    GCSDiscoveryStrategy,
    HDFSDiscoveryStrategy,
    MinIODiscoveryStrategy,
    S3DiscoveryStrategy,
)
from akaalEngine.discovery.strategies.timeseries import (
    InfluxDBDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.streaming import (
    EventHubsDiscoveryStrategy,
    KafkaDiscoveryStrategy,
    KinesisDiscoveryStrategy,
    PubSubDiscoveryStrategy,
    RabbitMQDiscoveryStrategy,
    PulsarDiscoveryStrategy,
)
from akaalEngine.discovery.strategies.warehouse import (
    BigQueryDiscoveryStrategy,
    DatabricksDiscoveryStrategy,
    RedshiftDiscoveryStrategy,
    SnowflakeDiscoveryStrategy,
    ClickHouseDiscoveryStrategy,
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
    CockroachDBDiscoveryStrategy,  # P7A Campaign B
    YugabyteDBDiscoveryStrategy,  # P7A Campaign B
    TiDBDiscoveryStrategy,  # P7A Campaign B
    SingleStoreDiscoveryStrategy,  # P7A Campaign B
    TeradataDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #39
    VerticaDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #40
    SAPHANADiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #41
    SAPASEDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #42
    InformixDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #43
    SpannerDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #45
    # Warehouse (4)
    SnowflakeDiscoveryStrategy,
    BigQueryDiscoveryStrategy,
    RedshiftDiscoveryStrategy,
    DatabricksDiscoveryStrategy,
    ClickHouseDiscoveryStrategy,  # P7A Campaign B
    # NoSQL & Search (8)
    MongoDBDiscoveryStrategy,
    CassandraDiscoveryStrategy,
    ScyllaDBDiscoveryStrategy,
    Neo4jDiscoveryStrategy,
    RedisDiscoveryStrategy,
    KeyDBDiscoveryStrategy,
    ElasticsearchDiscoveryStrategy,
    OpenSearchDiscoveryStrategy,
    DynamoDBDiscoveryStrategy,  # P7A Campaign B
    CouchbaseDiscoveryStrategy,  # P7A Campaign B
    CosmosDBDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #44
    # Application / SaaS (3)
    SalesforceDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #46
    ServiceNowDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #48
    SAPApplicationDiscoveryStrategy,  # P7A Campaign B (remaining-10), provider #47
    # Streaming (4)
    KafkaDiscoveryStrategy,
    KinesisDiscoveryStrategy,
    EventHubsDiscoveryStrategy,
    PubSubDiscoveryStrategy,
    RabbitMQDiscoveryStrategy,  # P7A Campaign B
    PulsarDiscoveryStrategy,  # P7A Campaign B
    # Storage (5)
    S3DiscoveryStrategy,
    GCSDiscoveryStrategy,
    AzureBlobDiscoveryStrategy,
    MinIODiscoveryStrategy,
    HDFSDiscoveryStrategy,
    # Time-series (1)
    InfluxDBDiscoveryStrategy,  # P7A Campaign B
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
    "CockroachDBDiscoveryStrategy",
    "YugabyteDBDiscoveryStrategy",
    "TiDBDiscoveryStrategy",
    "SingleStoreDiscoveryStrategy",
    "TeradataDiscoveryStrategy",
    "VerticaDiscoveryStrategy",
    "SAPHANADiscoveryStrategy",
    "SAPASEDiscoveryStrategy",
    "InformixDiscoveryStrategy",
    "SpannerDiscoveryStrategy",
    # Warehouse
    "SnowflakeDiscoveryStrategy",
    "BigQueryDiscoveryStrategy",
    "RedshiftDiscoveryStrategy",
    "DatabricksDiscoveryStrategy",
    "ClickHouseDiscoveryStrategy",
    # NoSQL
    "MongoDBDiscoveryStrategy",
    "CassandraDiscoveryStrategy",
    "ScyllaDBDiscoveryStrategy",
    "Neo4jDiscoveryStrategy",
    "RedisDiscoveryStrategy",
    "KeyDBDiscoveryStrategy",
    "ElasticsearchDiscoveryStrategy",
    "OpenSearchDiscoveryStrategy",
    "DynamoDBDiscoveryStrategy",
    "CouchbaseDiscoveryStrategy",
    "CosmosDBDiscoveryStrategy",
    "SalesforceDiscoveryStrategy",
    "ServiceNowDiscoveryStrategy",
    "SAPApplicationDiscoveryStrategy",
    # Streaming
    "KafkaDiscoveryStrategy",
    "KinesisDiscoveryStrategy",
    "EventHubsDiscoveryStrategy",
    "PubSubDiscoveryStrategy",
    "RabbitMQDiscoveryStrategy",
    "PulsarDiscoveryStrategy",
    # Storage
    "S3DiscoveryStrategy",
    "GCSDiscoveryStrategy",
    "AzureBlobDiscoveryStrategy",
    "MinIODiscoveryStrategy",
    "HDFSDiscoveryStrategy",
    "InfluxDBDiscoveryStrategy",
]
