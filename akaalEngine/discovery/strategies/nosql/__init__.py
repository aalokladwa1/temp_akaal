"""
akaalEngine.discovery.strategies.nosql
======================================
NoSQL, document, key-value, graph, and search engine discovery strategies.
"""

from akaalEngine.discovery.strategies.nosql.cassandra import CassandraDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.elasticsearch import ElasticsearchDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.keydb import KeyDBDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.mongodb import MongoDBDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.neo4j import Neo4jDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.opensearch import OpenSearchDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.redis import RedisDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.scylladb import ScyllaDBDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.dynamodb import DynamoDBDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.couchbase import CouchbaseDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.cosmosdb import CosmosDBDiscoveryStrategy

__all__ = [
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
]
