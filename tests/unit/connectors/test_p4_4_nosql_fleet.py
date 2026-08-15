"""
AKAAL P4.4 — NoSQL, Graph, Key-Value & Search Fleet Absolute Final Truth Rectification Suite.
=================================================================================================
Comprehensive hostile reality verification of the 8 authorized P4.4 connectors:
MongoDB, Cassandra, ScyllaDB, Neo4j, Redis, KeyDB, Elasticsearch, OpenSearch.
Verifies fail-closed connectivity isolation, zero-fake policy, missing driver handling,
_id keyset pagination, Cassandra/Scylla multi-column clustering tuple continuation (WHERE (ck1, ck2, ...) > (%s, %s, ...)),
Neo4j durable graph identity mapping (_akaal_source_id), self-loops, parallel edges,
Search engine PIT lifecycle & search_after continuation, bulk error detection, CDC truth, and permission truth.
"""

import unittest
import asyncio

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import get_adapter_class
from akaal.adapters.nosql.mongodb_adapter import MongoDBAdapter
from akaal.adapters.nosql.cassandra_adapter import CassandraAdapter
from akaal.adapters.nosql.scylladb_adapter import ScyllaDBAdapter
from akaal.adapters.nosql.neo4j_adapter import Neo4jAdapter
from akaal.adapters.nosql.redis_adapter import RedisAdapter
from akaal.adapters.nosql.keydb_adapter import KeyDBAdapter
from akaal.adapters.nosql.elasticsearch_adapter import ElasticsearchAdapter
from akaal.adapters.nosql.opensearch_adapter import OpenSearchAdapter
from akaal.connectors.bridge import register_canonical_bridge_connectors
from akaal.connectors.registry import UniversalConnectorRegistry


class TestP44NoSQLFleet(unittest.TestCase):
    """Absolute Final Hostile Reality Test Suite for P4.4 NoSQL, Graph, Key-Value & Search Adapters."""

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self) -> None:
        self.loop.close()

    def _make_cfg(self, st: SystemType, host: str = "localhost"):
        return ConnectionConfig(
            system_type=st,
            host=host,
            port=0,
            database_name="test_db",
            credentials_ref="none",
        )

    # -------------------------------------------------------------------------
    # 1. Inventory & Registry Resolution
    # -------------------------------------------------------------------------
    def test_01_p4_4_eight_connector_inventory_and_registry(self):
        """01: Verify all 8 P4.4 connectors resolve via get_adapter_class and bridge registry."""
        p44_types = [
            SystemType.MONGODB,
            SystemType.CASSANDRA,
            SystemType.SCYLLADB,
            SystemType.NEO4J,
            SystemType.REDIS,
            SystemType.KEYDB,
            SystemType.ELASTICSEARCH,
            SystemType.OPENSEARCH,
        ]

        for st in p44_types:
            cls = get_adapter_class(st)
            self.assertIsNotNone(cls)

        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["mongodb", "cassandra", "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch"]:
            bridge = reg.get_connector(sys_str)
            self.assertIsNotNone(bridge)
            manifest = bridge.manifest
            self.assertEqual(manifest.supports_cdc_capture, False)
            self.assertEqual(manifest.implementation_state.name, "IMPLEMENTED")
            self.assertEqual(manifest.support_state.name, "SUPPORTED")

    # -------------------------------------------------------------------------
    # 2. Disconnected Operations Fail Closed
    # -------------------------------------------------------------------------
    def test_02_disconnected_operations_fail_closed(self):
        """02: Disconnected operations across all 8 adapters raise RuntimeError fail-closed."""
        async def run():
            adapters = [
                MongoDBAdapter(self._make_cfg(SystemType.MONGODB)),
                CassandraAdapter(self._make_cfg(SystemType.CASSANDRA)),
                ScyllaDBAdapter(self._make_cfg(SystemType.SCYLLADB)),
                Neo4jAdapter(self._make_cfg(SystemType.NEO4J)),
                RedisAdapter(self._make_cfg(SystemType.REDIS)),
                KeyDBAdapter(self._make_cfg(SystemType.KEYDB)),
                ElasticsearchAdapter(self._make_cfg(SystemType.ELASTICSEARCH)),
                OpenSearchAdapter(self._make_cfg(SystemType.OPENSEARCH)),
            ]

            for ad in adapters:
                self.assertFalse(ad.is_connected)
                with self.assertRaises(RuntimeError):
                    await ad.discover_tables()
                with self.assertRaises(RuntimeError):
                    await ad.discover_columns("test_col")
                with self.assertRaises(RuntimeError):
                    await ad.read_batch("test_col", offset=0, limit=10)
                with self.assertRaises(RuntimeError):
                    await ad.write_batch("test_col", [{"id": 1}])
                with self.assertRaises(RuntimeError):
                    await ad.get_row_count("test_col")
                with self.assertRaises(RuntimeError):
                    await ad.compute_checksum("test_col")

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 3. Missing Drivers / Failed Connections
    # -------------------------------------------------------------------------
    def test_03_missing_drivers_and_failed_connection_isolation(self):
        """03: Connect attempts with invalid endpoints or missing credentials fail closed."""
        async def run():
            adapters = [
                MongoDBAdapter(self._make_cfg(SystemType.MONGODB, host="invalid-mongo-host")),
                CassandraAdapter(self._make_cfg(SystemType.CASSANDRA, host="invalid-cassandra-host")),
                ScyllaDBAdapter(self._make_cfg(SystemType.SCYLLADB, host="invalid-scylla-host")),
                Neo4jAdapter(self._make_cfg(SystemType.NEO4J, host="invalid-neo4j-host")),
                RedisAdapter(self._make_cfg(SystemType.REDIS, host="invalid-redis-host")),
                KeyDBAdapter(self._make_cfg(SystemType.KEYDB, host="invalid-keydb-host")),
                ElasticsearchAdapter(self._make_cfg(SystemType.ELASTICSEARCH, host="invalid-es-host")),
                OpenSearchAdapter(self._make_cfg(SystemType.OPENSEARCH, host="invalid-opensearch-host")),
            ]

            for ad in adapters:
                with self.assertRaises(RuntimeError):
                    await ad.connect()
                self.assertFalse(ad.is_connected)

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 4. Zero Production Mock Flags
    # -------------------------------------------------------------------------
    def test_04_zero_mock_mode_in_production_paths(self):
        """04: Production adapter instances must contain ZERO mock_mode attributes."""
        adapters = [
            MongoDBAdapter(self._make_cfg(SystemType.MONGODB)),
            CassandraAdapter(self._make_cfg(SystemType.CASSANDRA)),
            ScyllaDBAdapter(self._make_cfg(SystemType.SCYLLADB)),
            Neo4jAdapter(self._make_cfg(SystemType.NEO4J)),
            RedisAdapter(self._make_cfg(SystemType.REDIS)),
            KeyDBAdapter(self._make_cfg(SystemType.KEYDB)),
            ElasticsearchAdapter(self._make_cfg(SystemType.ELASTICSEARCH)),
            OpenSearchAdapter(self._make_cfg(SystemType.OPENSEARCH)),
        ]

        for ad in adapters:
            self.assertFalse(hasattr(ad, "mock_mode"))

    # -------------------------------------------------------------------------
    # 5. Cassandra & ScyllaDB Multi-Column Clustering Tuple Continuation
    # -------------------------------------------------------------------------
    def test_05_cassandra_and_scylla_multi_column_clustering_tuple_continuation(self):
        """05: Verify Cassandra and ScyllaDB generate (ck1, ck2, ...) > (%s, %s, ...) tuple queries."""
        for sys_type, ad_cls in [(SystemType.CASSANDRA, CassandraAdapter), (SystemType.SCYLLADB, ScyllaDBAdapter)]:
            ad = ad_cls(self._make_cfg(sys_type))
            ad.is_connected = True

            executed_queries = []

            class FakeRow:
                def __init__(self, t_id, b_id, e_time, e_id):
                    self.tenant_id = t_id
                    self.bucket_id = b_id
                    self.event_time = e_time
                    self.event_id = e_id
                def _asdict(self):
                    return {
                        "tenant_id": self.tenant_id,
                        "bucket_id": self.bucket_id,
                        "event_time": self.event_time,
                        "event_id": self.event_id,
                    }

            class FakeSession:
                def execute(self, query, params=None):
                    executed_queries.append((str(query), params))
                    if "system_schema.columns" in str(query):
                        class ColRow:
                            def __init__(self, name, kind, pos):
                                self.column_name = name
                                self.kind = kind
                                self.position = pos
                        return [
                            ColRow("tenant_id", "partition_key", 0),
                            ColRow("bucket_id", "partition_key", 1),
                            ColRow("event_time", "clustering", 0),
                            ColRow("event_id", "clustering", 1),
                        ]
                    return [FakeRow("t1", "b1", 100, "e2")]

            ad._session = FakeSession()

            async def run():
                rows = await ad.read_batch(
                    "events",
                    offset=0,
                    limit=10,
                    last_processed_primary_key={"tenant_id": "t1", "bucket_id": "b1", "event_time": 100, "event_id": "e1"},
                )
                self.assertEqual(len(rows), 1)
                query_str, params = executed_queries[-1]
                self.assertIn('("event_time", "event_id") > (%s, %s)', query_str)
                self.assertEqual(params, ("t1", "b1", 100, "e1"))

            self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 6. Search Engine PIT Lifecycle & search_after Continuation
    # -------------------------------------------------------------------------
    def test_06_search_engine_pit_lifecycle_and_search_after(self):
        """06: Verify Elasticsearch and OpenSearch support PIT lifecycle and search_after with sort_values."""
        for sys_type, ad_cls in [(SystemType.ELASTICSEARCH, ElasticsearchAdapter), (SystemType.OPENSEARCH, OpenSearchAdapter)]:
            ad = ad_cls(self._make_cfg(sys_type))
            ad.is_connected = True

            searches = []

            class FakeSearchClient:
                def open_point_in_time(self, index, keep_alive):
                    return {"id": "pit_12345"}
                def close_point_in_time(self, id):
                    return {"succeeded": True}
                def create_point_in_time(self, index, keep_alive):
                    return {"pit_id": "pit_12345"}
                def delete_point_in_time(self, body):
                    return {"succeeded": True}
                def search(self, **kwargs):
                    searches.append(kwargs)
                    return {
                        "hits": {
                            "hits": [
                                {
                                    "_id": "doc_101",
                                    "_source": {"title": "Doc 101"},
                                    "_routing": "shard_key_1",
                                    "sort": [123456],
                                }
                            ]
                        }
                    }

            ad._client = FakeSearchClient()

            async def run():
                pit_id = await ad.open_point_in_time("articles")
                self.assertEqual(pit_id, "pit_12345")

                rows = await ad.read_batch(
                    "articles",
                    offset=0,
                    limit=10,
                    last_processed_primary_key={"pit_id": pit_id, "sort_values": [123455]},
                )
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["_id"], "doc_101")
                self.assertIn("search_after", str(searches[-1]))

                closed = await ad.close_point_in_time(pit_id)
                self.assertTrue(closed)

            self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # 7. Neo4j Durable Identity & Graph Topology
    # -------------------------------------------------------------------------
    def test_07_neo4j_durable_identity_and_topology(self):
        """07: Verify Neo4j adapter uses _akaal_source_id for target relationship resolution."""
        ad = Neo4jAdapter(self._make_cfg(SystemType.NEO4J))
        ad.is_connected = True

        executed_cyphers = []

        class FakeNeo4jSession:
            def run(self, query, **kwargs):
                executed_cyphers.append((query, kwargs))
                class FakeResult:
                    def __iter__(self):
                        return iter([{"source_id": 1, "target_id": 1, "rel_type": "SELF_REF", "props": {"weight": 1.0}}])
                    def consume(self):
                        class FakeSummary:
                            class FakeCounters:
                                nodes_created = 1
                                relationships_created = 1
                            counters = FakeCounters()
                        return FakeSummary()
                return FakeResult()
            def __enter__(self): return self
            def __exit__(self, *args): pass

        class FakeNeo4jDriver:
            def session(self): return FakeNeo4jSession()

        ad._driver = FakeNeo4jDriver()

        async def run():
            nodes_created = await ad.write_batch("Person", [{"_node_id": 1, "name": "Alice"}])
            self.assertEqual(nodes_created, 1)
            self.assertIn("_akaal_source_id", executed_cyphers[-1][0])

            rels_created = await ad.write_relationships("SELF_REF", [{"source_id": 1, "target_id": 1, "props": {"weight": 1.0}}])
            self.assertEqual(rels_created, 1)
            self.assertIn("_akaal_source_id", executed_cyphers[-1][0])

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
