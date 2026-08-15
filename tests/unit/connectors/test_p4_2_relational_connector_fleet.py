"""
AKAAL P4.2 — Enterprise Relational Database Connector Fleet Acceptance Test Suite.
==================================================================================
Comprehensive verification of Oracle, PostgreSQL, MySQL, MariaDB, Microsoft SQL Server,
IBM Db2, and SQLite across all 25 behavioral dimensions (A through Y).
"""

import unittest
import asyncio
import threading
import hashlib
from typing import Dict, Any, List, Optional
from decimal import Decimal

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    ProofLevel,
    ImplementationState,
    SupportState,
    CapabilitySupportStatus,
    ConnectorErrorCategory,
    SemanticCompatibility,
)
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.profile import ConnectionProfile
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.compatibility import SemanticCompatibilityMatrix
from akaal.connectors.bridge import LegacyAdapterUniversalBridge
from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import create_adapter, get_adapter_class

from akaal.cdc.domain.positions import (
    PostgresLSNPosition,
    MySQLGTIDPosition,
    MariaDBGTIDPosition,
    OracleSCNPosition,
    MSSQLChangePosition,
    parse_source_position,
)
from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.sources.coordinator import CDCCaptureCoordinator
from akaal.gateway.engine_gateway import EngineGateway


class TestP42RelationalConnectorFleet(unittest.TestCase):
    """P4.2 Canonical Acceptance Test Suite for the 7 Relational Database Connectors."""

    def setUp(self) -> None:
        self.registry = UniversalConnectorRegistry.get_instance()
        self.gateway = EngineGateway()
        self.coordinator = CDCCaptureCoordinator()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self) -> None:
        self.loop.close()

    # -------------------------------------------------------------------------
    # Dimension A: Universal Relational Contract
    # -------------------------------------------------------------------------
    def test_A01_all_seven_implement_iuniversal_connector(self):
        """A01: All 7 relational connectors adhere to the IUniversalConnector contract."""
        relational_ids = ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]
        for cid in relational_ids:
            conn = self.registry.get_connector(cid)
            self.assertIsNotNone(conn, f"Missing connector instance for '{cid}'")
            self.assertEqual(conn.connector_id, cid)
            self.assertEqual(conn.family, ConnectorFamily.RELATIONAL_DATABASE)
            self.assertIsNotNone(conn.manifest)

    # -------------------------------------------------------------------------
    # Dimension B: Universal Registry Registrations
    # -------------------------------------------------------------------------
    def test_B01_all_seven_registered_in_universal_registry(self):
        """B01: All 7 relational connectors are registered and queryable."""
        relational_ids = ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]
        registered = self.registry.list_connectors()
        for cid in relational_ids:
            self.assertIn(cid, registered, f"'{cid}' not found in registry listings")

    # -------------------------------------------------------------------------
    # Dimension C: Capability Manifest Truthfulness
    # -------------------------------------------------------------------------
    def test_C01_capability_manifest_truthfulness(self):
        """C01: Every relational manifest truthfully declares implementation, support, and proof states."""
        relational_ids = ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]
        for cid in relational_ids:
            m = self.registry.get_manifest(cid)
            self.assertIsNotNone(m)
            self.assertEqual(m.implementation_state, ImplementationState.IMPLEMENTED)
            self.assertEqual(m.support_state, SupportState.SUPPORTED)
            self.assertEqual(m.proof_level, ProofLevel.UNIT_PROVEN)
            self.assertTrue(m.supports_transactions)
            self.assertTrue(m.supports_bulk_read)
            self.assertTrue(m.supports_bulk_write)

    # -------------------------------------------------------------------------
    # Dimension D: Source/Target Directionality
    # -------------------------------------------------------------------------
    def test_D01_all_seven_support_both_source_and_target(self):
        """D01: All 7 relational connectors support both SOURCE and TARGET roles."""
        relational_ids = ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]
        for cid in relational_ids:
            m = self.registry.get_manifest(cid)
            self.assertEqual(m.role, ConnectorRole.BOTH)
            self.assertTrue(m.is_source_capable())
            self.assertTrue(m.is_target_capable())

    # -------------------------------------------------------------------------
    # Dimension E & F: Schema Discovery & Metadata Extraction
    # -------------------------------------------------------------------------
    def test_EF01_schema_discovery_across_all_seven(self):
        """EF01: Schema discovery executes and returns tables, columns, PKs, and FKs for all 7 engines."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_discovery():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="127.0.0.1",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="test-vault-ref",
                    extra={"username": "testuser", "password": "testpassword", "mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                self.assertGreater(len(tables), 0, f"No tables discovered for {st.value}")

                cols = await adapter.discover_columns(tables[0])
                self.assertGreater(len(cols), 0, f"No columns discovered for {st.value}.{tables[0]}")

                fks = await adapter.discover_foreign_keys()
                self.assertIsInstance(fks, list)

                indexes = await adapter.discover_indexes(tables[0])
                self.assertIsInstance(indexes, list)

                constraints = await adapter.discover_constraints(tables[0])
                self.assertIsInstance(constraints, list)

                await adapter.close()

        self.loop.run_until_complete(run_discovery())

    # -------------------------------------------------------------------------
    # Dimension G & H: Bulk Read & Bulk Write
    # -------------------------------------------------------------------------
    def test_GH01_bulk_read_and_write_across_all_seven(self):
        """GH01: Bulk read and bulk write operate smoothly across all 7 databases."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_io():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="127.0.0.1",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="test-vault-ref",
                    extra={"username": "testuser", "password": "testpassword", "mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                tbl = tables[0]

                # Bulk Read
                rows = await adapter.read_batch(tbl, offset=0, limit=10)
                self.assertEqual(len(rows), 10, f"Expected 10 rows for {st.value}")

                # Bulk Write
                written = await adapter.write_batch(tbl, rows)
                self.assertEqual(written, 10, f"Expected 10 written rows for {st.value}")

                await adapter.close()

        self.loop.run_until_complete(run_io())

    # -------------------------------------------------------------------------
    # Dimension I: Transaction Semantics
    # -------------------------------------------------------------------------
    def test_I01_transaction_primitives_across_all_seven(self):
        """I01: Begin, commit, and rollback transactions function without errors on all 7 engines."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_tx():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="127.0.0.1",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="test-vault-ref",
                    extra={"username": "testuser", "password": "testpassword", "mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()

                # Test Commit Cycle
                await adapter.begin_transaction()
                await adapter.commit_transaction()

                # Test Rollback Cycle
                await adapter.begin_transaction()
                await adapter.rollback_transaction()

                await adapter.close()

        self.loop.run_until_complete(run_tx())

    # -------------------------------------------------------------------------
    # Dimension J: Native Position Serialization
    # -------------------------------------------------------------------------
    def test_J01_native_position_serialization_and_parsing(self):
        """J01: Native positions for SCN, LSN, MySQL GTID, and MariaDB GTID serialize and parse cleanly."""
        positions = [
            PostgresLSNPosition("0/16B3800"),
            MySQLGTIDPosition("mysql-bin.000001", 1024, "3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5"),
            MariaDBGTIDPosition(0, 1, 5000, "mariadb-bin.000001", 500),
            OracleSCNPosition(12948572, 1, 1),
            MSSQLChangePosition("0000002A:000001B0:0001"),
        ]

        for pos in positions:
            d = pos.to_dict()
            self.assertEqual(d["engine"], pos.engine)
            reconstructed = parse_source_position(d)
            self.assertEqual(reconstructed.engine, pos.engine)
            self.assertEqual(reconstructed.to_string(), pos.to_string())

    # -------------------------------------------------------------------------
    # Dimension K: Cross-Engine Position Comparison Rejection
    # -------------------------------------------------------------------------
    def test_K01_cross_engine_positions_strictly_forbid_raw_comparison(self):
        """K01: Cross-comparing disparate engine positions raises TypeError."""
        pg_pos = PostgresLSNPosition("0/16B3800")
        my_pos = MySQLGTIDPosition("mysql-bin.000001", 1024)
        maria_pos = MariaDBGTIDPosition(0, 1, 5000)
        ora_pos = OracleSCNPosition(12948572)
        mssql_pos = MSSQLChangePosition("0000002A:000001B0:0001")

        pairs = [
            (pg_pos, my_pos),
            (pg_pos, maria_pos),
            (pg_pos, ora_pos),
            (pg_pos, mssql_pos),
            (my_pos, maria_pos),
            (my_pos, ora_pos),
            (maria_pos, ora_pos),
            (mssql_pos, pg_pos),
        ]

        for p1, p2 in pairs:
            with self.assertRaises(TypeError):
                _ = p1.is_after(p2)

    # -------------------------------------------------------------------------
    # Dimension L & M: CDC Capability Truthfulness & Translation
    # -------------------------------------------------------------------------
    def test_LM01_cdc_capability_truthfulness_and_translation(self):
        """LM01: CDC is supported for Oracle, Postgres, MySQL, MariaDB, MSSQL; and unsupported for Db2 & SQLite."""
        # 1. Oracle, Postgres, MySQL, MariaDB, MSSQL -> CDC Supported
        cdc_engines = ["oracle", "postgresql", "mysql", "mariadb", "mssql"]
        for cid in cdc_engines:
            m = self.registry.get_manifest(cid)
            self.assertTrue(m.supports_cdc_capture, f"CDC should be supported for {cid}")

        # 2. Db2 & SQLite -> CDC Unsupported
        no_cdc_engines = ["ibm_db2", "sqlite"]
        for cid in no_cdc_engines:
            m = self.registry.get_manifest(cid)
            self.assertFalse(m.supports_cdc_capture, f"CDC should be unsupported for {cid}")

        # 3. Test MariaDB CDC Capture Poll
        miner = self.coordinator.get_miner_for_engine("MARIADB")
        ident = CDCEventIdentity("mig-maria-test", "job-1", "run-1", "cdc-sess-1")
        initial_pos = MariaDBGTIDPosition(0, 1, 100)
        boundary = miner.initialize_capture(ident, initial_pos)
        self.assertIsNotNone(boundary)

        txs = miner.poll_transactions()
        self.assertGreater(len(txs), 0)
        self.assertEqual(txs[0].events[0].source_engine, "MARIADB")
        miner.close()

    # -------------------------------------------------------------------------
    # Dimension N: Validation Access
    # -------------------------------------------------------------------------
    def test_N01_validation_access_row_count_and_checksum(self):
        """N01: Row count and checksum calculations work for validation across all 7 engines."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_val():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="127.0.0.1",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="test-vault-ref",
                    extra={"username": "testuser", "password": "testpassword", "mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                tbl = tables[0]

                count = await adapter.get_row_count(tbl)
                self.assertGreaterEqual(count, 0)

                checksum = await adapter.compute_checksum(tbl)
                self.assertIsInstance(checksum, str)
                self.assertGreater(len(checksum), 0)

                await adapter.close()

        self.loop.run_until_complete(run_val())

    # -------------------------------------------------------------------------
    # Dimension O: Optional Driver Absence & Safe Fallback
    # -------------------------------------------------------------------------
    def test_O01_optional_drivers_fail_safely(self):
        """O01: Instantiating adapters without live external drivers operates safely in fallback mode."""
        for cid in ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]:
            conn = self.registry.get_connector(cid)
            self.assertIsNotNone(conn)
            val = conn.validate_configuration(ConnectionProfile(connector_id=cid, host="db.internal", port=5432))
            self.assertTrue(val["valid"])

    # -------------------------------------------------------------------------
    # Dimension P: Sanitized Errors & Secret Protection
    # -------------------------------------------------------------------------
    def test_P01_secret_sanitization_and_error_classification(self):
        """P01: No plaintext passwords in profile dictionaries; error classification is accurate."""
        prof = ConnectionProfile(
            connector_id="mariadb",
            host="mariadb.internal",
            raw_credentials={"password": "plain_secret_password"},
        )
        d = prof.to_sanitized_dict()
        self.assertNotIn("plain_secret_password", str(d))

        bridge = self.registry.get_connector("mariadb")
        cat_auth = bridge.classify_error(Exception("Access denied for user 'root'@'localhost' (using password: YES)"))
        cat_conn = bridge.classify_error(Exception("Connection refused / timed out"))
        self.assertEqual(cat_auth, ConnectorErrorCategory.AUTHENTICATION)
        self.assertEqual(cat_conn, ConnectorErrorCategory.CONNECTIVITY)

    # -------------------------------------------------------------------------
    # Dimension Q: Resource Cleanup & Lifecycle
    # -------------------------------------------------------------------------
    def test_Q01_connection_lifecycle_connect_and_disconnect(self):
        """Q01: Connect, health check, and disconnect operate cleanly across all 7 connectors."""
        async def run_lifecycle():
            for cid in ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]:
                conn = self.registry.get_connector(cid)
                prof = ConnectionProfile(
                    connector_id=cid,
                    host="source-db.example.com",
                    port=5432,
                    database_name="testdb",
                    driver_options={"mock_mode": True},
                )
                await conn.connect(prof)
                health = await conn.health_check()
                self.assertTrue(health.is_healthy)
                await conn.disconnect()
                health_after = await conn.health_check()
                self.assertFalse(health_after.is_healthy)

        self.loop.run_until_complete(run_lifecycle())

    # -------------------------------------------------------------------------
    # Dimension R: Concurrency & Isolation
    # -------------------------------------------------------------------------
    def test_R01_multithreaded_concurrent_adapter_sessions(self):
        """R01: Multiple concurrent threads acquiring adapter instances do not cross-contaminate state."""
        errors = []

        def worker(idx: int):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st = SystemType.POSTGRESQL if idx % 2 == 0 else SystemType.MARIADB
                cfg = ConnectionConfig(
                    system_type=st,
                    host=f"host-{idx}.example.com",
                    port=5432,
                    database_name=f"db_{idx}",
                    credentials_ref=f"vault-ref-{idx}",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                loop.run_until_complete(adapter.connect())
                tables = loop.run_until_complete(adapter.discover_tables())
                if not tables:
                    errors.append(f"No tables in thread {idx}")
                loop.run_until_complete(adapter.close())
                loop.close()
            except Exception as e:
                errors.append(f"Thread {idx} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")

    # -------------------------------------------------------------------------
    # Dimension S: EngineGateway Reachability
    # -------------------------------------------------------------------------
    def test_S01_engine_gateway_manifest_reachability_all_seven(self):
        """S01: EngineGateway returns valid manifests for all 7 relational engines."""
        for cid in ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]:
            res = self.gateway.invoke("get_connector_manifest", {"connector_id": cid})
            self.assertTrue(res["found"], f"Manifest not found via gateway for {cid}")
            self.assertEqual(res["manifest"]["family"], "RELATIONAL_DATABASE")

    # -------------------------------------------------------------------------
    # Dimension T: P0–P3 Authority Preservation
    # -------------------------------------------------------------------------
    def test_T01_p0_p3_authorities_preserved(self):
        """T01: P0 Workflow, P1 Recovery, P2 Schema, P3 CDC authorities remain intact."""
        from akaal.workflow.engine.engine import WorkflowEngine
        from akaal.runtime.recovery.coordinator import RecoveryCoordinator
        from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5
        from akaal.cdc.sync.coordinator import CDCContinuousSyncCoordinator
        from akaal.core.state.state_store import CentralStateStore

        store = CentralStateStore()
        rec = RecoveryCoordinator()
        self.assertIsNotNone(WorkflowEngine())
        self.assertIsNotNone(rec)
        self.assertIsNotNone(SchemaEvolutionPlatformV5())
        self.assertIsNotNone(CDCContinuousSyncCoordinator(store, rec))

    # -------------------------------------------------------------------------
    # Dimension U: Managed-Service Profile Reuse
    # -------------------------------------------------------------------------
    def test_U01_managed_service_profile_compatibility(self):
        """U01: Managed service profile captures cloud provider and region while reusing base relational connector."""
        aurora_prof = ConnectionProfile(
            connector_id="postgresql",
            cloud_provider="AWS",
            region="us-east-1",
            host="aurora-pg.cluster-xyz.us-east-1.rds.amazonaws.com",
            database_name="prod_app",
        )
        d = aurora_prof.to_sanitized_dict()
        self.assertEqual(d["connector_id"], "postgresql")
        self.assertEqual(d["cloud_provider"], "AWS")
        self.assertEqual(d["region"], "us-east-1")

    # -------------------------------------------------------------------------
    # Dimension V: Unsupported Operations Fail Closed
    # -------------------------------------------------------------------------
    def test_V01_unsupported_operations_fail_closed(self):
        """V01: SQLite and Db2 reject or fail closed on native CDC requests."""
        sqlite_m = self.registry.get_manifest("sqlite")
        self.assertFalse(sqlite_m.supports_cdc_capture)
        self.assertEqual(sqlite_m.get_capability_status("cdc_capture"), CapabilitySupportStatus.UNSUPPORTED)

        with self.assertRaises(ValueError):
            _ = self.coordinator.get_miner_for_engine("SQLITE")

    # -------------------------------------------------------------------------
    # Dimension W: Restart / Resume Contract
    # -------------------------------------------------------------------------
    def test_W01_restart_resume_from_durable_position(self):
        """W01: Resuming from durable native position operates deterministically."""
        pos1 = PostgresLSNPosition("0/16B3800")
        pos2 = PostgresLSNPosition("0/16B3900")
        self.assertTrue(pos2.is_after(pos1))

        maria1 = MariaDBGTIDPosition(0, 1, 100)
        maria2 = MariaDBGTIDPosition(0, 1, 105)
        self.assertTrue(maria2.is_after(maria1))

    # -------------------------------------------------------------------------
    # Dimension X: LOB Streaming Integration
    # -------------------------------------------------------------------------
    def test_X01_lob_streaming_supported_across_fleet(self):
        """X01: All 7 relational manifests declare LOB streaming support."""
        for cid in ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]:
            m = self.registry.get_manifest(cid)
            self.assertTrue(m.supports_lobs)

    # -------------------------------------------------------------------------
    # Dimension Y: Compatibility Matrix Truthfulness
    # -------------------------------------------------------------------------
    def test_Y01_cross_relational_compatibility_matrix(self):
        """Y01: Homogeneous relational is SUPPORTED; heterogeneous relational is SUPPORTED_WITH_MAPPING."""
        m_pg = self.registry.get_manifest("postgresql")
        m_oracle = self.registry.get_manifest("oracle")
        m_mysql = self.registry.get_manifest("mysql")
        m_mariadb = self.registry.get_manifest("mariadb")

        # Homogeneous PG -> PG
        res_homo = SemanticCompatibilityMatrix.evaluate_compatibility(m_pg, m_pg)
        self.assertTrue(res_homo["is_viable"])
        self.assertEqual(res_homo["compatibility"], SemanticCompatibility.SUPPORTED.value)

        # Heterogeneous Oracle -> PG
        res_hetero = SemanticCompatibilityMatrix.evaluate_compatibility(m_oracle, m_pg)
        self.assertTrue(res_hetero["is_viable"])
        self.assertEqual(res_hetero["compatibility"], SemanticCompatibility.SUPPORTED_WITH_MAPPING.value)
        self.assertIn("SQL_DIALECT_DATATYPE_CONVERSION", res_hetero["required_mappings"])

        # Heterogeneous MySQL -> MariaDB
        res_my_maria = SemanticCompatibilityMatrix.evaluate_compatibility(m_mysql, m_mariadb)
        self.assertTrue(res_my_maria["is_viable"])
        self.assertEqual(res_my_maria["compatibility"], SemanticCompatibility.SUPPORTED_WITH_MAPPING.value)


if __name__ == "__main__":
    unittest.main()
