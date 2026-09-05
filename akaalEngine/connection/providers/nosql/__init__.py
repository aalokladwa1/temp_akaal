"""
akaalEngine.connection.providers.nosql
======================================
NoSQL, Document, Graph, KV, and Search provider strategies.
"""

from akaalEngine.connection.providers.nosql.mongodb import MongoDBProviderStrategy
from akaalEngine.connection.providers.nosql.cassandra import CassandraProviderStrategy
from akaalEngine.connection.providers.nosql.scylladb import ScyllaDBProviderStrategy
from akaalEngine.connection.providers.nosql.neo4j import Neo4jProviderStrategy
from akaalEngine.connection.providers.nosql.redis import RedisProviderStrategy
from akaalEngine.connection.providers.nosql.keydb import KeyDBProviderStrategy
from akaalEngine.connection.providers.nosql.elasticsearch import ElasticsearchProviderStrategy
from akaalEngine.connection.providers.nosql.opensearch import OpenSearchProviderStrategy
from akaalEngine.connection.providers.nosql.dynamodb import DynamoDBProviderStrategy
from akaalEngine.connection.providers.nosql.couchbase import CouchbaseProviderStrategy
from akaalEngine.connection.providers.nosql.cosmosdb import CosmosDBProviderStrategy

__all__ = [
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
    "CosmosDBProviderStrategy",
]
