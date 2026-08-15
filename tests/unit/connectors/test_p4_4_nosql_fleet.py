"""
AKAAL P4.4 — NoSQL, Graph, Key-Value & Search Fleet Comprehensive Hostile Reality Suite.
========================================================================================
Hostile reality verification of the 8 authorized P4.4 connectors:
MongoDB, Cassandra, ScyllaDB, Neo4j, Redis, KeyDB, Elasticsearch, OpenSearch.
Verifies fail-closed connectivity isolation, zero-fake policy, missing driver handling,
bulk error detection, CDC capability truth, and bridge manifest registration.
"""

import unittest
import asyncio

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import get_adapter_class, create_adapter
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
    """Expanded Hostile Reality Test Suite for P4.4 NoSQL, Graph, Key-Value & Search Adapters."""

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
    # 5. Bulk Write Error Handling (Elasticsearch & OpenSearch)
    # -------------------------------------------------------------------------
    def test_05_search_bulk_write_error_propagation(self):
        """05: Verify Elasticsearch and OpenSearch raise RuntimeError on bulk write item errors."""
        es = ElasticsearchAdapter(self._make_cfg(SystemType.ELASTICSEARCH))
        es.is_connected = True

        class FakeESClient:
            def bulk(self, operations):
                return {
                    "errors": True,
                    "items": [{"index": {"error": {"type": "mapper_parsing_exception", "reason": "failed to parse"}}}],
                }

        es._client = FakeESClient()

        async def run_es():
            with self.assertRaises(RuntimeError) as ctx:
                await es.write_batch("my_index", [{"col1": "val1"}])
            self.assertIn("Elasticsearch bulk write failed with errors", str(ctx.exception))

        self.loop.run_until_complete(run_es())

        os_adapter = OpenSearchAdapter(self._make_cfg(SystemType.OPENSEARCH))
        os_adapter.is_connected = True

        class FakeOSClient:
            def bulk(self, body):
                return {
                    "errors": True,
                    "items": [{"index": {"error": {"type": "mapper_parsing_exception", "reason": "failed to parse"}}}],
                }

        os_adapter._client = FakeOSClient()

        async def run_os():
            with self.assertRaises(RuntimeError) as ctx:
                await os_adapter.write_batch("my_index", [{"col1": "val1"}])
            self.assertIn("OpenSearch bulk write failed with errors", str(ctx.exception))

        self.loop.run_until_complete(run_os())

    # -------------------------------------------------------------------------
    # 6. CDC Capability Truth
    # -------------------------------------------------------------------------
    def test_06_cdc_capability_flags_truthful(self):
        """06: All 8 P4.4 NoSQL/Search connectors declare supports_cdc_capture = False."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["mongodb", "cassandra", "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch"]:
            bridge = reg.get_connector(sys_str)
            manifest = bridge.manifest
            self.assertFalse(manifest.supports_cdc_capture)
            self.assertFalse(manifest.supports_cdc_position_resume)

    # -------------------------------------------------------------------------
    # 7. Source & Target Roles
    # -------------------------------------------------------------------------
    def test_07_source_target_roles_both(self):
        """07: All 8 connectors support BOTH source extraction and target ingestion roles."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["mongodb", "cassandra", "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch"]:
            bridge = reg.get_connector(sys_str)
            manifest = bridge.manifest
            self.assertTrue(manifest.supports_bulk_read)
            self.assertTrue(manifest.supports_bulk_write)

    # -------------------------------------------------------------------------
    # 8. Proof Level Truth
    # -------------------------------------------------------------------------
    def test_08_proof_level_truth(self):
        """08: Verify proof levels are UNIT_PROVEN and NOT LIVE_SYSTEM_PROVEN until cloud run."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["mongodb", "cassandra", "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch"]:
            bridge = reg.get_connector(sys_str)
            manifest = bridge.manifest
            self.assertEqual(manifest.proof_level.name, "UNIT_PROVEN")


if __name__ == "__main__":
    unittest.main()
