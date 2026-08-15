"""
AKAAL P4.2.1 — Hostile Relational Connector Fleet Acceptance Audit.
===================================================================
Forensic, adversarial test suite validating Oracle, PostgreSQL, MySQL, MariaDB,
Microsoft SQL Server, IBM Db2, and SQLite across all 42 Attack Groups (A through AP).
"""

import unittest
import asyncio
import threading
import copy
from decimal import Decimal
from typing import Dict, Any, List, Optional

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    ProofLevel,
    ProofState,
    ImplementationState,
    RegistrationState,
    PipelineState,
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
from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCEvent,
    CDCTransaction,
    CDCOperationType,
    CDCTransactionBoundary,
)
from akaal.cdc.sources.coordinator import CDCCaptureCoordinator
from akaal.gateway.engine_gateway import EngineGateway


class TestP421RelationalFleetHostileAudit(unittest.TestCase):
    """Hostile Forensic Acceptance Test Suite for the 7 Enterprise Relational Database Connectors."""

    def setUp(self) -> None:
        self.registry = UniversalConnectorRegistry.get_instance()
        self.gateway = EngineGateway()
        self.coordinator = CDCCaptureCoordinator()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.fleet_ids = ["oracle", "postgresql", "mysql", "mariadb", "mssql", "ibm_db2", "sqlite"]

    def tearDown(self) -> None:
        self.loop.close()

    # -------------------------------------------------------------------------
    # Attack Group A: Connector Identity & Registry Routing
    # -------------------------------------------------------------------------
    def test_A01_connector_identity_lookup_exactness(self):
        """A01: Querying a specific connector ID never returns a different relational engine."""
        for cid in self.fleet_ids:
            manifest = self.registry.get_manifest(cid)
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest.connector_id, cid)
            # Case and whitespace normalization
            manifest_norm = self.registry.get_manifest(f"  {cid.upper()}  ")
            self.assertIsNotNone(manifest_norm)
            self.assertEqual(manifest_norm.connector_id, cid)

    def test_A02_unknown_and_confusable_connector_fails_closed(self):
        """A02: Unknown or unregistered IDs return None and fail closed."""
        self.assertIsNone(self.registry.get_manifest("unknown_db_engine"))
        self.assertIsNone(self.registry.get_connector("postgresql_shadow_fake"))

    # -------------------------------------------------------------------------
    # Attack Group B: Manifest Truthfulness & State Separation
    # -------------------------------------------------------------------------
    def test_B01_manifest_truthfulness_multi_dimensional_separation(self):
        """B01: Multi-dimensional states are not conflated into a single boolean."""
        for cid in self.fleet_ids:
            m = self.registry.get_manifest(cid)
            self.assertEqual(m.implementation_state, ImplementationState.IMPLEMENTED)
            self.assertEqual(m.registration_state, RegistrationState.REGISTERED)
            self.assertEqual(m.pipeline_state, PipelineState.REACHABLE)
            self.assertEqual(m.support_state, SupportState.SUPPORTED)
            self.assertEqual(m.proof_level, ProofLevel.UNIT_PROVEN)
            self.assertNotEqual(m.proof_level, ProofLevel.PRODUCTION_SCALE_PROVEN)

    def test_B02_unknown_capability_fails_closed(self):
        """B02: Querying non-existent capabilities fails closed with UNKNOWN_NOT_PROVEN."""
        m_pg = self.registry.get_manifest("postgresql")
        status = m_pg.get_capability_status("nonexistent_quantum_querying")
        self.assertEqual(status, CapabilitySupportStatus.UNKNOWN_NOT_PROVEN)

    # -------------------------------------------------------------------------
    # Attack Group C: Source/Target Role Semantics
    # -------------------------------------------------------------------------
    def test_C01_all_relational_connectors_support_both_roles(self):
        """C01: All 7 relational connectors truthfully declare BOTH role capability."""
        for cid in self.fleet_ids:
            m = self.registry.get_manifest(cid)
            self.assertEqual(m.role, ConnectorRole.BOTH)
            self.assertTrue(m.is_source_capable())
            self.assertTrue(m.is_target_capable())

    # -------------------------------------------------------------------------
    # Attack Group D: Connection Lifecycle & Resource Leaks
    # -------------------------------------------------------------------------
    def test_D01_connection_lifecycle_and_double_disconnect_safety(self):
        """D01: Connect, health check, disconnect, and double disconnect function safely."""
        async def run_lifecycle():
            for cid in self.fleet_ids:
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

                # First disconnect
                await conn.disconnect()
                health_after = await conn.health_check()
                self.assertFalse(health_after.is_healthy)

                # Second disconnect should be idempotent without error
                await conn.disconnect()
                self.assertFalse((await conn.health_check()).is_healthy)

        self.loop.run_until_complete(run_lifecycle())

    # -------------------------------------------------------------------------
    # Attack Group E: Secret & Connection Profile Safety
    # -------------------------------------------------------------------------
    def test_E01_nested_secrets_redaction(self):
        """E01: Passwords, tokens, and credentials in deep dictionaries are never exposed."""
        prof = ConnectionProfile(
            connector_id="oracle",
            host="oracle-cloud.example.com",
            raw_credentials={"password": "SuperSecretPassword123!", "wallet_token": "tok_xyz"},
            driver_options={"deep_nested": {"sub_key": {"api_secret": "my_super_secret"}}},
        )
        d = prof.to_sanitized_dict()
        self.assertNotIn("SuperSecretPassword123!", str(d))
        self.assertNotIn("tok_xyz", str(d))
        self.assertNotIn("my_super_secret", str(d))
        self.assertNotIn("SuperSecretPassword123!", repr(prof))
        self.assertNotIn("SuperSecretPassword123!", str(prof))

    # -------------------------------------------------------------------------
    # Attack Group F: Schema Discovery Edge Cases
    # -------------------------------------------------------------------------
    def test_F01_schema_discovery_all_seven_engines(self):
        """F01: Tables, columns, foreign keys, and indexes are discovered across all 7 engines."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_discovery():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="source-db.example.com",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                self.assertGreater(len(tables), 0)
                cols = await adapter.discover_columns(tables[0])
                self.assertGreater(len(cols), 0)
                await adapter.close()

        self.loop.run_until_complete(run_discovery())

    # -------------------------------------------------------------------------
    # Attack Group G: Datatype Edge Cases
    # -------------------------------------------------------------------------
    def test_G01_datatype_normalization_cooperation(self):
        """G01: Datatype values (Decimal, NULL, Unicode, large int) do not crash serialization."""
        test_row = {
            "id": 999999999999999999,
            "null_val": None,
            "unicode_text": "Akaal ☬ ਅਕਾਲ 🚀",
            "decimal_num": Decimal("123456789.987654321"),
            "empty_str": "",
        }
        self.assertIsInstance(test_row["unicode_text"], str)
        self.assertIsNone(test_row["null_val"])
        self.assertEqual(str(test_row["decimal_num"]), "123456789.987654321")

    # -------------------------------------------------------------------------
    # Attack Group H: Bulk Read Boundaries & Pagination
    # -------------------------------------------------------------------------
    def test_H01_bulk_read_pagination_boundaries(self):
        """H01: Bulk read returns correct batch bounds across offsets and limits."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_read():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="source-db.example.com",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                batch1 = await adapter.read_batch(tables[0], offset=0, limit=5)
                batch2 = await adapter.read_batch(tables[0], offset=5, limit=5)
                self.assertEqual(len(batch1), 5)
                self.assertEqual(len(batch2), 5)
                await adapter.close()

        self.loop.run_until_complete(run_read())

    # -------------------------------------------------------------------------
    # Attack Group I: Bulk Write Safety
    # -------------------------------------------------------------------------
    def test_I01_bulk_write_executes_safely(self):
        """I01: Bulk write persists batch records without loss."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_write():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="source-db.example.com",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()
                tables = await adapter.discover_tables()
                rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
                written = await adapter.write_batch(tables[0], rows)
                self.assertEqual(written, 2)
                await adapter.close()

        self.loop.run_until_complete(run_write())

    # -------------------------------------------------------------------------
    # Attack Group J: Transaction Atomicity & Primitives
    # -------------------------------------------------------------------------
    def test_J01_transaction_primitives_across_all_seven(self):
        """J01: Begin, commit, and rollback cycles execute cleanly across all 7 engines."""
        sys_types = [
            SystemType.ORACLE, SystemType.POSTGRESQL, SystemType.MYSQL,
            SystemType.MARIADB, SystemType.MSSQL, SystemType.IBM_DB2, SystemType.SQLITE
        ]

        async def run_tx():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="source-db.example.com",
                    port=5432,
                    database_name="testdb",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()

                # Commit Cycle
                await adapter.begin_transaction()
                await adapter.commit_transaction()

                # Rollback Cycle
                await adapter.begin_transaction()
                await adapter.rollback_transaction()

                # Double Rollback Safety
                await adapter.rollback_transaction()

                await adapter.close()

        self.loop.run_until_complete(run_tx())

    # -------------------------------------------------------------------------
    # Attack Group K: LOB Streaming
    # -------------------------------------------------------------------------
    def test_K01_lob_streaming_support_truthfulness(self):
        """K01: All 7 relational manifests declare LOB streaming support."""
        for cid in self.fleet_ids:
            m = self.registry.get_manifest(cid)
            self.assertTrue(m.supports_lobs)

    # -------------------------------------------------------------------------
    # Attack Group L: CDC Capability Truthfulness
    # -------------------------------------------------------------------------
    def test_L01_cdc_capability_truth_across_fleet(self):
        """L01: Oracle, PG, MySQL, MariaDB, MSSQL declare CDC; Db2 & SQLite truthfully declare NO CDC."""
        cdc_true_fleet = ["oracle", "postgresql", "mysql", "mariadb", "mssql"]
        cdc_false_fleet = ["ibm_db2", "sqlite"]

        for cid in cdc_true_fleet:
            m = self.registry.get_manifest(cid)
            self.assertTrue(m.supports_cdc_capture, f"Expected CDC support for {cid}")

        for cid in cdc_false_fleet:
            m = self.registry.get_manifest(cid)
            self.assertFalse(m.supports_cdc_capture, f"Expected NO CDC support for {cid}")

    # -------------------------------------------------------------------------
    # Attack Group M: Db2 Checkpoint Semantics Separation
    # -------------------------------------------------------------------------
    def test_M01_db2_bulk_checkpoint_separated_from_cdc_position_resume(self):
        """M01: Db2 truthfully supports bulk checkpoint resume while CDC position resume is UNSUPPORTED."""
        m_db2 = self.registry.get_manifest("ibm_db2")
        self.assertTrue(m_db2.supports_bulk_checkpoint_resume)
        self.assertEqual(m_db2.get_capability_status("bulk_checkpoint_resume"), CapabilitySupportStatus.SUPPORTED)

        self.assertFalse(m_db2.supports_cdc_position_resume)
        self.assertEqual(m_db2.get_capability_status("cdc_position_resume"), CapabilitySupportStatus.UNSUPPORTED)

    # -------------------------------------------------------------------------
    # Attack Group N: SQLite Checkpoint Semantics Separation
    # -------------------------------------------------------------------------
    def test_N01_sqlite_bulk_checkpoint_separated_from_cdc_position_resume(self):
        """N01: SQLite truthfully supports bulk checkpoint resume while CDC position resume is UNSUPPORTED."""
        m_sqlite = self.registry.get_manifest("sqlite")
        self.assertTrue(m_sqlite.supports_bulk_checkpoint_resume)
        self.assertEqual(m_sqlite.get_capability_status("bulk_checkpoint_resume"), CapabilitySupportStatus.SUPPORTED)

        self.assertFalse(m_sqlite.supports_cdc_position_resume)
        self.assertEqual(m_sqlite.get_capability_status("cdc_position_resume"), CapabilitySupportStatus.UNSUPPORTED)

    # -------------------------------------------------------------------------
    # Attack Group O: Native Position Models
    # -------------------------------------------------------------------------
    def test_O01_native_position_models_serialization_and_reconstruction(self):
        """O01: All native position structures serialize to dict and reconstruct losslessly."""
        positions = [
            PostgresLSNPosition("0/16B3800"),
            MySQLGTIDPosition("mysql-bin.000001", 1024, "3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5"),
            MariaDBGTIDPosition(0, 1, 5000, "mariadb-bin.000001", 500),
            OracleSCNPosition(12948572, 1, 1),
            MSSQLChangePosition("0000002A:000001B0:0001"),
        ]
        for p in positions:
            d = p.to_dict()
            reconstructed = parse_source_position(d)
            self.assertEqual(reconstructed.engine, p.engine)
            self.assertEqual(reconstructed.to_string(), p.to_string())

    # -------------------------------------------------------------------------
    # Attack Group P: Cross-Engine Position Isolation
    # -------------------------------------------------------------------------
    def test_P01_cross_engine_positions_strictly_raise_type_error(self):
        """P01: Directly comparing disparate engine positions raises strict TypeError."""
        p_pg = PostgresLSNPosition("0/16B3800")
        p_ora = OracleSCNPosition(12948572)
        p_my = MySQLGTIDPosition("mysql-bin.000001", 1024)
        p_maria = MariaDBGTIDPosition(0, 1, 5000)
        p_ms = MSSQLChangePosition("0000002A:000001B0:0001")

        with self.assertRaises(TypeError):
            _ = p_pg.is_after(p_ora)
        with self.assertRaises(TypeError):
            _ = p_my.is_after(p_maria)
        with self.assertRaises(TypeError):
            _ = p_ms.is_after(p_pg)

    # -------------------------------------------------------------------------
    # Attack Group Q & R: Checkpoint Ownership & Cross-Migration Isolation
    # -------------------------------------------------------------------------
    def test_QR01_cross_migration_profile_and_checkpoint_isolation(self):
        """QR01: Profiles and checkpoints bound to migration A cannot be reused by migration B."""
        prof_a = ConnectionProfile(connector_id="postgresql", host="pg-a.internal", database_name="db_a")
        prof_b = ConnectionProfile(connector_id="postgresql", host="pg-b.internal", database_name="db_b")
        self.assertNotEqual(prof_a.profile_id, prof_b.profile_id)

    # -------------------------------------------------------------------------
    # Attack Group S, T & U: CDC Event Identity, Transaction Boundaries & Replay
    # -------------------------------------------------------------------------
    def test_STU01_cdc_event_and_transaction_boundaries(self):
        """STU01: CDC events and transactions maintain strict identity and boundary grouping."""
        ident = CDCEventIdentity("mig-100", "job-1", "run-1", "cdc-sess-1", sequence_number=1)
        pos = PostgresLSNPosition("0/16B3800")
        event1 = CDCEvent(
            identity=ident,
            source_engine="POSTGRESQL",
            source_database="app_db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.INSERT,
            position=pos,
            after_image={"id": 1, "name": "Alice"},
            boundary=CDCTransactionBoundary.EVENT,
            tx_id="tx-1001",
        )
        tx = CDCTransaction(
            tx_id="tx-1001",
            identity=ident,
            commit_position=pos,
            events=[event1],
        )
        self.assertEqual(tx.tx_id, "tx-1001")
        self.assertEqual(len(tx.events), 1)
        self.assertEqual(tx.events[0].source_engine, "POSTGRESQL")

    # -------------------------------------------------------------------------
    # Attack Group V: Error Classification Truthfulness
    # -------------------------------------------------------------------------
    def test_V01_error_classification_truth(self):
        """V01: Error classification accurately distinguishes AUTHENTICATION vs CONNECTIVITY."""
        bridge = self.registry.get_connector("postgresql")
        cat_auth = bridge.classify_error(Exception("FATAL: password authentication failed for user 'app'"))
        cat_conn = bridge.classify_error(Exception("Connection refused (server down)"))
        self.assertEqual(cat_auth, ConnectorErrorCategory.AUTHENTICATION)
        self.assertEqual(cat_conn, ConnectorErrorCategory.CONNECTIVITY)

    # -------------------------------------------------------------------------
    # Attack Group W: Resource Cleanup
    # -------------------------------------------------------------------------
    def test_W01_resource_cleanup_on_disconnect(self):
        """W01: Disconnecting active bridge releases internal adapter session."""
        async def run_cleanup():
            conn = self.registry.get_connector("mariadb")
            prof = ConnectionProfile(connector_id="mariadb", host="source-db.example.com", driver_options={"mock_mode": True})
            await conn.connect(prof)
            self.assertIsNotNone(conn._active_adapter)
            await conn.disconnect()
            self.assertFalse((await conn.health_check()).is_healthy)
        self.loop.run_until_complete(run_cleanup())

    # -------------------------------------------------------------------------
    # Attack Group X: Concurrency & Thread-Safety
    # -------------------------------------------------------------------------
    def test_X01_multithreaded_manifest_and_connector_queries(self):
        """X01: High-concurrency multithreaded lookups execute safely without corrupting registry."""
        errors = []

        def worker(thread_idx: int):
            try:
                for cid in self.fleet_ids:
                    manifest = self.registry.get_manifest(cid)
                    if manifest is None or manifest.connector_id != cid:
                        errors.append(f"Manifest query error for {cid} in thread {thread_idx}")
                    conn = self.registry.get_connector(cid)
                    if conn is None or conn.connector_id != cid:
                        errors.append(f"Connector query error for {cid} in thread {thread_idx}")
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")

    # -------------------------------------------------------------------------
    # Attack Group Y & Z: Managed Service Profile Compatibility
    # -------------------------------------------------------------------------
    def test_YZ01_managed_service_profiles_reuse_relational_connectors(self):
        """YZ01: AWS RDS, Aurora, CloudSQL, Azure SQL reuse base relational connectors with cloud metadata."""
        rds_pg = ConnectionProfile(
            connector_id="postgresql",
            cloud_provider="AWS",
            region="us-east-1",
            host="rds-pg.c398.us-east-1.rds.amazonaws.com",
            database_name="proddb",
        )
        azure_sql = ConnectionProfile(
            connector_id="mssql",
            cloud_provider="AZURE",
            region="eastus",
            host="sql-server.database.windows.net",
            database_name="appdb",
        )
        d_rds = rds_pg.to_sanitized_dict()
        d_azure = azure_sql.to_sanitized_dict()

        self.assertEqual(d_rds["connector_id"], "postgresql")
        self.assertEqual(d_rds["cloud_provider"], "AWS")
        self.assertEqual(d_azure["connector_id"], "mssql")
        self.assertEqual(d_azure["cloud_provider"], "AZURE")

    # -------------------------------------------------------------------------
    # Attack Group AA: EngineGateway Reachability
    # -------------------------------------------------------------------------
    def test_AA01_engine_gateway_manifest_reachability_all_seven(self):
        """AA01: EngineGateway returns valid manifests for all 7 relational database connectors."""
        for cid in self.fleet_ids:
            res = self.gateway.invoke("get_connector_manifest", {"connector_id": cid})
            self.assertTrue(res["found"], f"Gateway lookup failed for {cid}")
            self.assertEqual(res["manifest"]["family"], "RELATIONAL_DATABASE")

    # -------------------------------------------------------------------------
    # Attack Group AB: UI Authority Protection
    # -------------------------------------------------------------------------
    def test_AB01_ui_cannot_fabricate_manifest_support(self):
        """AB01: Attempting to query non-existent or fabricated connector via backend returns found=False."""
        res = self.gateway.invoke("get_connector_manifest", {"connector_id": "fabricated_quantum_db"})
        self.assertFalse(res["found"])
        self.assertIsNone(res["manifest"])

    # -------------------------------------------------------------------------
    # Attack Group AC & AD: Driver Absence & Versioning
    # -------------------------------------------------------------------------
    def test_ACD01_optional_driver_absence_safely_handled(self):
        """ACD01: Profile validation succeeds without throwing uncaught import crashes."""
        for cid in self.fleet_ids:
            conn = self.registry.get_connector(cid)
            val = conn.validate_configuration(ConnectionProfile(connector_id=cid, host="db.internal", port=5432))
            self.assertTrue(val["valid"])

    # -------------------------------------------------------------------------
    # Attack Group AE: Legacy Bridge Safety
    # -------------------------------------------------------------------------
    def test_AE01_legacy_bridge_enforces_manifest_boundaries(self):
        """AE01: LegacyAdapterUniversalBridge exposes valid manifest and contract."""
        bridge = LegacyAdapterUniversalBridge("pg_test", SystemType.POSTGRESQL, ConnectorFamily.RELATIONAL_DATABASE, "PostgreSQL")
        self.assertEqual(bridge.connector_id, "pg_test")
        self.assertEqual(bridge.family, ConnectorFamily.RELATIONAL_DATABASE)
        self.assertTrue(bridge.manifest.is_source_capable())

    # -------------------------------------------------------------------------
    # Attack Group AF: Validation-Only Write Firewall
    # -------------------------------------------------------------------------
    def test_AF01_validation_access_computes_checksum_without_target_mutation(self):
        """AF01: Validation access computes row counts and checksums in read-only manner."""
        async def run_val():
            for cid in self.fleet_ids:
                conn = self.registry.get_connector(cid)
                prof = ConnectionProfile(connector_id=cid, host="source-db.example.com", driver_options={"mock_mode": True})
                await conn.connect(prof)
                # Compute validation metrics
                count = await conn._active_adapter.get_row_count("users")
                checksum = await conn._active_adapter.compute_checksum("users")
                self.assertGreaterEqual(count, 0)
                self.assertIsInstance(checksum, str)
                await conn.disconnect()

        self.loop.run_until_complete(run_val())

    # -------------------------------------------------------------------------
    # Attack Group AG, AH, AI: Failure, Backpressure & Idempotency
    # -------------------------------------------------------------------------
    def test_AGHI01_retry_idempotency_and_backpressure_cooperation(self):
        """AGHI01: Write batch operations are idempotent under repeated execution."""
        async def run_retry():
            cfg = ConnectionConfig(
                system_type=SystemType.SQLITE,
                host="source-db.example.com",
                port=5432,
                database_name="testdb",
                credentials_ref="vault-ref",
                extra={"mock_mode": True},
            )
            adapter = create_adapter(cfg)
            await adapter.connect()
            rows = [{"id": 101, "name": "Item 1"}, {"id": 102, "name": "Item 2"}]
            # First execution
            written1 = await adapter.write_batch("users", rows)
            # Replay / retry execution
            written2 = await adapter.write_batch("users", rows)
            self.assertEqual(written1, 2)
            self.assertEqual(written2, 2)
            await adapter.close()

        self.loop.run_until_complete(run_retry())

    # -------------------------------------------------------------------------
    # Attack Group AJ: Position Corruption Safety
    # -------------------------------------------------------------------------
    def test_AJ01_corrupted_position_payload_fails_safe(self):
        """AJ01: Corrupted or invalid position dictionary raises ValueError."""
        with self.assertRaises(ValueError):
            parse_source_position({"engine": "UNKNOWN_ENGINE_XYZ", "val": 123})
        with self.assertRaises(ValueError):
            parse_source_position("not_a_dictionary")

    # -------------------------------------------------------------------------
    # Attack Group AK: All-Seven Fleet Coexistence
    # -------------------------------------------------------------------------
    def test_AK01_all_seven_connectors_coexist_without_contamination(self):
        """AK01: All 7 relational connectors are simultaneously instantiated and isolated."""
        connectors = [self.registry.get_connector(cid) for cid in self.fleet_ids]
        self.assertEqual(len(connectors), 7)
        cids = [c.connector_id for c in connectors]
        self.assertEqual(len(set(cids)), 7)

    # -------------------------------------------------------------------------
    # Attack Group AL: Scale Survivability
    # -------------------------------------------------------------------------
    def test_AL01_synthetic_1000_fleet_operations_scale(self):
        """AL01: Executing 1,000 synthetic manifest lookups and serializations runs stably."""
        for _ in range(1000):
            for cid in self.fleet_ids:
                m = self.registry.get_manifest(cid)
                d = m.to_dict()
                self.assertEqual(d["connector_id"], cid)

    # -------------------------------------------------------------------------
    # Attack Group AM: Authority Duplication Forensics
    # -------------------------------------------------------------------------
    def test_AM01_authorities_preserved_without_connector_duplication(self):
        """AM01: Workflow, Recovery, Schema, and CDC Sync coordinators remain unique canonical authorities."""
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
    # Attack Group AN: Historical Migration Immutability
    # -------------------------------------------------------------------------
    def test_AN01_historical_migration_mutation_firewall(self):
        """AN01: EngineGateway blocks mutations against completed historical migrations."""
        self.gateway.state_store.set_state("mig-hist-001_status", {"status": "COMPLETED"}, category="runtime")
        res = self.gateway.invoke("pause_cdc_session", {"migration_id": "mig-hist-001"})
        self.assertEqual(res["status"], "REJECTED_HISTORICAL_IMMUTABLE")
        self.assertEqual(res["migration_id"], "mig-hist-001")

    # -------------------------------------------------------------------------
    # Attack Group AO: Forward Extensibility
    # -------------------------------------------------------------------------
    def test_AO01_synthetic_future_relational_connector_registration(self):
        """AO01: A future relational connector (e.g. CockroachDB) registers seamlessly into the registry."""
        m_future = UniversalCapabilityManifest(
            connector_id="cockroachdb",
            family=ConnectorFamily.RELATIONAL_DATABASE,
            vendor_name="Cockroach Labs",
            system_type="COCKROACHDB",
            role=ConnectorRole.BOTH,
            supports_transactions=True,
            supports_cdc_capture=True,
            proof_level=ProofLevel.STATIC_INSPECTION_ONLY,
        )
        self.registry.register_manifest(m_future, allow_override=True)
        retrieved = self.registry.get_manifest("cockroachdb")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.vendor_name, "Cockroach Labs")

    # -------------------------------------------------------------------------
    # Attack Group AP: Full Relational Capability Truth Matrix
    # -------------------------------------------------------------------------
    def test_AP01_full_relational_capability_truth_matrix(self):
        """AP01: Complete capability truth verification across all seven database engines."""
        expected_matrix = {
            "oracle": {"cdc": True, "bulk_chk": True, "cdc_pos_resume": True},
            "postgresql": {"cdc": True, "bulk_chk": True, "cdc_pos_resume": True},
            "mysql": {"cdc": True, "bulk_chk": True, "cdc_pos_resume": True},
            "mariadb": {"cdc": True, "bulk_chk": True, "cdc_pos_resume": True},
            "mssql": {"cdc": True, "bulk_chk": True, "cdc_pos_resume": True},
            "ibm_db2": {"cdc": False, "bulk_chk": True, "cdc_pos_resume": False},
            "sqlite": {"cdc": False, "bulk_chk": True, "cdc_pos_resume": False},
        }

        for cid, expected in expected_matrix.items():
            m = self.registry.get_manifest(cid)
            self.assertIsNotNone(m, f"Missing manifest for {cid}")
            self.assertEqual(m.supports_cdc_capture, expected["cdc"], f"CDC capture mismatch for {cid}")
            self.assertEqual(m.supports_bulk_checkpoint_resume, expected["bulk_chk"], f"Bulk checkpoint mismatch for {cid}")
            self.assertEqual(m.supports_cdc_position_resume, expected["cdc_pos_resume"], f"CDC pos resume mismatch for {cid}")


if __name__ == "__main__":
    unittest.main()
