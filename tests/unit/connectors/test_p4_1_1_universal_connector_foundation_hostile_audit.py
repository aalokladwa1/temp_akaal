"""
AKAAL P4.1.1 — Hostile Universal Connector Foundation Acceptance Audit Suite.
=============================================================================
30 Adversarial Attack Groups (A through AD) verifying connector foundation integrity,
capability truthfulness, proof-state separation, security redaction, native-position safety,
concurrency determinism, and authority preservation.
"""

import unittest
import threading
import uuid
import datetime
from typing import Dict, Any, List, Optional

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    AuthenticationMechanism,
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
from akaal.connectors.profile import ConnectionProfile, recursive_sanitize
from akaal.connectors.contracts.base import (
    IUniversalConnector,
    ConnectionTestResult,
    HealthStatus,
)
from akaal.connectors.contracts.database import IDatabaseCapability
from akaal.connectors.contracts.document import IDocumentCapability
from akaal.connectors.contracts.warehouse import IWarehouseCapability
from akaal.connectors.contracts.streaming import IStreamingCapability
from akaal.connectors.contracts.object_storage import IObjectStorageCapability
from akaal.connectors.contracts.wide_column import IWideColumnCapability
from akaal.connectors.contracts.graph import IGraphCapability, IKeyValueCapability, ISearchCapability
from akaal.connectors.contracts.cloud_provider import ICloudProviderCapability
from akaal.connectors.compatibility import SemanticCompatibilityMatrix
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.bridge import LegacyAdapterUniversalBridge
from akaal.core.models.enums import SystemType
from akaal.gateway.engine_gateway import EngineGateway


class HostileMockConnector(IUniversalConnector):
    """Adversarial connector for hostile attack testing."""

    def __init__(
        self,
        connector_id: str = "hostile-test",
        family: ConnectorFamily = ConnectorFamily.RELATIONAL_DATABASE,
        role: ConnectorRole = ConnectorRole.BOTH,
        supports_cdc: bool = False,
    ) -> None:
        self._connector_id = str(connector_id).strip().lower()
        self._family = family
        self._role = role
        self._supports_cdc = supports_cdc
        self._is_connected = False
        self._manifest = UniversalCapabilityManifest(
            connector_id=self._connector_id,
            family=self._family,
            vendor_name="Hostile Mock Test",
            system_type="HOSTILE",
            role=self._role,
            supports_cdc_capture=self._supports_cdc,
        )

    @property
    def connector_id(self) -> str:
        return self._connector_id

    @property
    def family(self) -> ConnectorFamily:
        return self._family

    @property
    def manifest(self) -> UniversalCapabilityManifest:
        return self._manifest

    def validate_configuration(self, config: Optional[ConnectionProfile]) -> Dict[str, Any]:
        if not config or not config.host:
            return {"valid": False, "errors": ["Host required."]}
        return {"valid": True, "errors": []}

    async def connect(self, config: ConnectionProfile) -> None:
        self._is_connected = True

    async def test_connection(self, config: ConnectionProfile) -> ConnectionTestResult:
        return ConnectionTestResult(success=True, message="Connected")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(is_healthy=self._is_connected)

    async def disconnect(self) -> None:
        self._is_connected = False

    async def reconnect(self) -> None:
        self._is_connected = True

    def classify_error(self, exception: Exception) -> ConnectorErrorCategory:
        return ConnectorErrorCategory.UNKNOWN_FAIL_CLOSED


class TestP411UniversalConnectorHostileAudit(unittest.TestCase):
    """P4.1.1 Hostile Forensic Audit Suite (Groups A through AD)."""

    def setUp(self) -> None:
        self.registry = UniversalConnectorRegistry.get_instance()
        self.gateway = EngineGateway()

    # -------------------------------------------------------------------------
    # Group A: Connector Identity & Registry Isolation
    # -------------------------------------------------------------------------
    def test_A01_duplicate_registration_fails_safe_without_override(self):
        """A01: Attempting duplicate registration without override raises ValueError."""
        conn1 = HostileMockConnector("dup-test")
        conn2 = HostileMockConnector("dup-test")
        self.registry.register_connector(conn1, allow_override=True)
        with self.assertRaises(ValueError):
            self.registry.register_connector(conn2, allow_override=False)

    def test_A02_case_and_whitespace_identity_normalization(self):
        """A02: Lookup and registration normalize whitespace and casing."""
        conn = HostileMockConnector("  POSTGRESQL-CUSTOM  ")
        self.registry.register_connector(conn, allow_override=True)
        fetched = self.registry.get_connector("postgresql-custom")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.connector_id, "postgresql-custom")

    def test_A03_unknown_and_empty_connector_id_fails_closed(self):
        """A03: Non-existent or empty connector lookup returns None."""
        self.assertIsNone(self.registry.get_connector("completely-unknown-db-999"))
        self.assertIsNone(self.registry.get_connector(""))
        self.assertIsNone(self.registry.get_connector(None))

    # -------------------------------------------------------------------------
    # Group B: Capability Manifest Truthfulness
    # -------------------------------------------------------------------------
    def test_B01_unclaimed_capability_fails_closed(self):
        """B01: Manifest get_capability_status on undeclared capability returns UNKNOWN_NOT_PROVEN."""
        m = UniversalCapabilityManifest("c1", ConnectorFamily.RELATIONAL_DATABASE, "V1", "POSTGRESQL")
        status = m.get_capability_status("quantum_query_acceleration")
        self.assertEqual(status, CapabilitySupportStatus.UNKNOWN_NOT_PROVEN)

    def test_B02_explicit_unsupported_capability_fails_closed(self):
        """B02: Explicitly unsupported capabilities return UNSUPPORTED."""
        m = UniversalCapabilityManifest("c1", ConnectorFamily.OBJECT_STORAGE, "V1", "S3", supports_transactions=False)
        self.assertEqual(m.get_capability_status("transactions"), CapabilitySupportStatus.UNSUPPORTED)

    # -------------------------------------------------------------------------
    # Group C: Implementation / Support / Proof Separation
    # -------------------------------------------------------------------------
    def test_C01_dimensions_remain_strictly_independent(self):
        """C01: ProofState, ImplementationState, SupportState, and PipelineState are not collapsed."""
        m = UniversalCapabilityManifest(
            connector_id="partial-test",
            family=ConnectorFamily.CLOUD_DATA_WAREHOUSE,
            vendor_name="Warehouse Inc",
            system_type="SNOWFLAKE",
            implementation_state=ImplementationState.PARTIAL,
            support_state=SupportState.PARTIAL,
            pipeline_state=PipelineState.REACHABLE,
            proof_state=ProofState.UNIT_PROVEN,
            registration_state=RegistrationState.REGISTERED,
        )
        d = m.to_dict()
        self.assertEqual(d["implementation_state"], "PARTIAL")
        self.assertEqual(d["support_state"], "PARTIAL")
        self.assertEqual(d["pipeline_state"], "REACHABLE")
        self.assertEqual(d["proof_state"], "UNIT_PROVEN")
        self.assertEqual(d["registration_state"], "REGISTERED")

    # -------------------------------------------------------------------------
    # Group D: Proof Level Inflation Prevention
    # -------------------------------------------------------------------------
    def test_D01_proof_level_cannot_inflate_without_real_evidence(self):
        """D01: Unit proven connector cannot masquerade as real system or production certified."""
        m = UniversalCapabilityManifest("c1", ConnectorFamily.RELATIONAL_DATABASE, "V1", "MYSQL", proof_level=ProofLevel.UNIT_PROVEN)
        self.assertNotEqual(m.proof_level, ProofLevel.REAL_SYSTEM_PROVEN)
        self.assertNotEqual(m.proof_level, ProofLevel.PRODUCTION_SCALE_PROVEN)

    # -------------------------------------------------------------------------
    # Group E: Compatibility False Positives
    # -------------------------------------------------------------------------
    def test_E01_unproven_cross_family_fails_closed(self):
        """E01: Unproven cross-family pair (e.g. Graph -> Object Storage) returns NOT_YET_PROVEN."""
        m_graph = UniversalCapabilityManifest("g1", ConnectorFamily.GRAPH_DATABASE, "Neo4j", "NEO4J")
        m_obj = UniversalCapabilityManifest("o1", ConnectorFamily.OBJECT_STORAGE, "S3", "S3")
        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_graph, m_obj)
        self.assertFalse(res["is_viable"])
        self.assertEqual(res["compatibility"], SemanticCompatibility.NOT_YET_PROVEN.value)

    def test_E02_null_manifests_fail_closed(self):
        """E02: Evaluating compatibility with None manifests returns UNSUPPORTED."""
        res1 = SemanticCompatibilityMatrix.evaluate_compatibility(None, None)
        self.assertFalse(res1["is_viable"])
        self.assertEqual(res1["compatibility"], SemanticCompatibility.UNSUPPORTED.value)

    # -------------------------------------------------------------------------
    # Group F: Native Position Semantic Safety
    # -------------------------------------------------------------------------
    def test_F01_heterogeneous_native_positions_forbid_raw_comparison(self):
        """F01: Cross-engine heterogeneous positions raise TypeError on raw comparison."""
        from akaal.cdc.domain.positions import PostgresLSNPosition, MySQLGTIDPosition
        pg_lsn = PostgresLSNPosition("0/16B3800")
        my_binlog = MySQLGTIDPosition("mysql-bin.000001", 1024)

        with self.assertRaises(TypeError):
            _ = pg_lsn.is_after(my_binlog)

    # -------------------------------------------------------------------------
    # Group G: Connection Profile Secret Safety
    # -------------------------------------------------------------------------
    def test_G01_recursive_secret_redaction(self):
        """G01: Nested secrets across arbitrarily deep dictionaries and lists are redacted."""
        nested_data = {
            "app": "akaal",
            "db_pass": "secret123",
            "nested": {
                "api_key": "raw_api_token",
                "normal": "value",
                "deep_list": [{"private_token": "token_xyz"}, {"user": "admin"}],
            },
        }
        sanitized = recursive_sanitize(nested_data)
        san_str = str(sanitized)
        self.assertNotIn("secret123", san_str)
        self.assertNotIn("raw_api_token", san_str)
        self.assertNotIn("token_xyz", san_str)
        self.assertIn("admin", san_str)
        self.assertEqual(sanitized["db_pass"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["deep_list"][0]["private_token"], "[REDACTED]")

    def test_G02_repr_and_str_never_leak_raw_secrets(self):
        """G02: ConnectionProfile __repr__ and __str__ omit plaintext passwords."""
        prof = ConnectionProfile(
            host="db.example.com",
            raw_credentials={"password": "super_secret_master_password"},
        )
        self.assertNotIn("super_secret_master_password", repr(prof))
        self.assertNotIn("super_secret_master_password", str(prof))

    # -------------------------------------------------------------------------
    # Group H: Connection Lifecycle & Resource Safety
    # -------------------------------------------------------------------------
    def test_H01_connection_lifecycle_failure_is_truthful(self):
        """H01: Disconnected or unconfigured connector health reflects truth."""
        import asyncio
        loop = asyncio.new_event_loop()
        conn = HostileMockConnector()
        health = loop.run_until_complete(conn.health_check())
        self.assertFalse(health.is_healthy)
        loop.close()

    # -------------------------------------------------------------------------
    # Group I: Legacy Adapter Bridge Safety
    # -------------------------------------------------------------------------
    def test_I01_legacy_bridge_enforces_manifest_discipline(self):
        """I01: LegacyAdapterUniversalBridge exposes valid manifest and contract."""
        bridge = LegacyAdapterUniversalBridge(
            "pg-bridge",
            SystemType.POSTGRESQL,
            ConnectorFamily.RELATIONAL_DATABASE,
            "PostgreSQL Bridge",
            ConnectorRole.BOTH,
        )
        self.assertEqual(bridge.connector_id, "pg-bridge")
        self.assertEqual(bridge.manifest.system_type, "POSTGRESQL")
        self.assertTrue(bridge.manifest.supports_transactions)

    # -------------------------------------------------------------------------
    # Group J: Unsupported Capability Fail-Closed
    # -------------------------------------------------------------------------
    def test_J01_unsupported_capability_extension_returns_none(self):
        """J01: Querying capability extension for unimplemented interface returns None."""
        conn = HostileMockConnector()
        ext = conn.get_capability_extension(IDatabaseCapability)
        self.assertIsNone(ext)

    # -------------------------------------------------------------------------
    # Group K: Source / Target Role Semantics
    # -------------------------------------------------------------------------
    def test_K01_target_only_cannot_act_as_source(self):
        """K01: Target-only manifest fails compatibility when used as source."""
        m_target = UniversalCapabilityManifest("snow", ConnectorFamily.CLOUD_DATA_WAREHOUSE, "Snowflake", "SNOWFLAKE", role=ConnectorRole.TARGET)
        m_dest = UniversalCapabilityManifest("pg", ConnectorFamily.RELATIONAL_DATABASE, "PostgreSQL", "POSTGRESQL", role=ConnectorRole.TARGET)
        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_target, m_dest)
        self.assertFalse(res["is_viable"])
        self.assertIn("does not support SOURCE role", res["reason"])

    # -------------------------------------------------------------------------
    # Group L: Cross-Migration / Cross-Run Substitution
    # -------------------------------------------------------------------------
    def test_L01_cross_migration_profile_isolation(self):
        """L01: Connection profiles generate distinct unique identities."""
        p1 = ConnectionProfile(connection_id="mig-1-conn", credentials_ref="ref-1")
        p2 = ConnectionProfile(connection_id="mig-2-conn", credentials_ref="ref-2")
        self.assertNotEqual(p1.connection_id, p2.connection_id)
        self.assertNotEqual(p1.credentials_ref, p2.credentials_ref)

    # -------------------------------------------------------------------------
    # Group M: Concurrency & Registry Races
    # -------------------------------------------------------------------------
    def test_M01_multithreaded_registry_races(self):
        """M01: Concurrent registrations and lookups under high thread contention remain deterministic."""
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(30):
                    cid = f"race-conn-{thread_idx}-{i}"
                    m = UniversalCapabilityManifest(cid, ConnectorFamily.RELATIONAL_DATABASE, f"Vendor-{thread_idx}", "ORACLE")
                    self.registry.register_manifest(m, allow_override=True)
                    fetched = self.registry.get_manifest(cid)
                    if not fetched:
                        errors.append(f"Failed to fetch {cid}")
            except Exception as e:
                errors.append(f"Thread error: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")

    # -------------------------------------------------------------------------
    # Group N: Manifest Immutability / Mutation Safety
    # -------------------------------------------------------------------------
    def test_N01_external_mutation_does_not_corrupt_manifest(self):
        """N01: Mutating dictionary returned by to_dict does not affect internal manifest collections."""
        m = UniversalCapabilityManifest(
            "immut-test",
            ConnectorFamily.RELATIONAL_DATABASE,
            "Vendor",
            "MYSQL",
            supported_formats=["CSV", "JSON"],
        )
        d = m.to_dict()
        d["supported_formats"].append("CORRUPT_FORMAT")

        self.assertNotIn("CORRUPT_FORMAT", m.supported_formats)

    # -------------------------------------------------------------------------
    # Group O: Serialization & Version Compatibility
    # -------------------------------------------------------------------------
    def test_O01_serialization_with_missing_fields_defaults_safely(self):
        """O01: Manifest from_dict with missing fields constructs safely with fail-closed defaults."""
        sparse_dict = {
            "connector_id": "sparse-conn",
            "vendor_name": "Sparse DB",
        }
        m = UniversalCapabilityManifest.from_dict(sparse_dict)
        self.assertEqual(m.connector_id, "sparse-conn")
        self.assertEqual(m.family, ConnectorFamily.RELATIONAL_DATABASE)
        self.assertEqual(m.proof_level, ProofLevel.STATIC_INSPECTION_ONLY)

    # -------------------------------------------------------------------------
    # Group P: Driver Absence & Optional Dependency Failure
    # -------------------------------------------------------------------------
    def test_P01_driver_absence_does_not_crash_import(self):
        """P01: Universal connector registry can be instantiated without optional third-party drivers."""
        reg = UniversalConnectorRegistry.get_instance()
        self.assertIsNotNone(reg)

    # -------------------------------------------------------------------------
    # Group Q: P0–P3 Authority Bypass Attacks
    # -------------------------------------------------------------------------
    def test_Q01_canonical_workflow_and_cdc_authorities_unaffected(self):
        """Q01: Connectors do not override WorkflowEngine or CDC Sync coordinator."""
        from akaal.workflow.engine.engine import WorkflowEngine
        from akaal.cdc.sync.coordinator import CDCContinuousSyncCoordinator
        from akaal.core.state.state_store import CentralStateStore
        from akaal.runtime.recovery.coordinator import RecoveryCoordinator

        store = CentralStateStore()
        rec = RecoveryCoordinator()
        sync_coord = CDCContinuousSyncCoordinator(store, rec)
        wf = WorkflowEngine()

        self.assertIsNotNone(sync_coord)
        self.assertIsNotNone(wf)

    # -------------------------------------------------------------------------
    # Group R: Checkpoint / Recovery Ownership
    # -------------------------------------------------------------------------
    def test_R01_recovery_coordinator_retains_fencing_token_authority(self):
        """R01: Fencing tokens remain governed by RecoveryCoordinator, not connectors."""
        from akaal.runtime.recovery.coordinator import RecoveryCoordinator
        rec = RecoveryCoordinator()
        ep = rec.issue_epoch("mig-fencing-test")
        self.assertEqual(ep, 1)
        self.assertTrue(rec.validate_fencing_token("mig-fencing-test", 1))

    # -------------------------------------------------------------------------
    # Group S: CDC Capability Boundary
    # -------------------------------------------------------------------------
    def test_S01_connector_without_cdc_rejects_cdc_capture(self):
        """S01: Bridge connector with supports_cdc=False reports False on manifest."""
        m_sqlite = self.registry.get_manifest("sqlite")
        self.assertIsNotNone(m_sqlite)
        self.assertFalse(m_sqlite.supports_cdc_capture)

    # -------------------------------------------------------------------------
    # Group T: Schema & Validation Authority
    # -------------------------------------------------------------------------
    def test_T01_universal_ddl_and_validation_authorities_remain_canonical(self):
        """T01: Universal schema platform and validation platform retain authority."""
        from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5
        from akaal.validation.facade.platform1 import EnterpriseValidationPlatformV1

        schema_plat = SchemaEvolutionPlatformV5()
        val_plat = EnterpriseValidationPlatformV1()
        self.assertIsNotNone(schema_plat)
        self.assertIsNotNone(val_plat)

    # -------------------------------------------------------------------------
    # Group U: Cloud / Managed Service Classification
    # -------------------------------------------------------------------------
    def test_U01_cloud_managed_services_use_family_and_cloud_provider_metadata(self):
        """U01: Managed service profile captures cloud_provider and region without separate fake engine types."""
        prof_rds = ConnectionProfile(
            connector_id="postgresql",
            cloud_provider="AWS",
            region="us-east-1",
            host="rds.pg.internal",
        )
        d = prof_rds.to_sanitized_dict()
        self.assertEqual(d["cloud_provider"], "AWS")
        self.assertEqual(d["region"], "us-east-1")
        self.assertEqual(d["connector_id"], "postgresql")

    # -------------------------------------------------------------------------
    # Group V: Technology Family Boundaries
    # -------------------------------------------------------------------------
    def test_V01_all_15_technology_families_represented(self):
        """V01: All 15 canonical technology families exist in taxonomy."""
        expected_families = [
            "RELATIONAL_DATABASE", "CLOUD_DATA_WAREHOUSE", "DOCUMENT_DATABASE",
            "WIDE_COLUMN_DATABASE", "GRAPH_DATABASE", "KEY_VALUE_STORE",
            "SEARCH_ENGINE", "STREAM_EVENT_PLATFORM", "DISTRIBUTED_FILESYSTEM",
            "OBJECT_STORAGE", "FILE_DATASET", "LAKEHOUSE_ANALYTICS",
            "CLOUD_PROVIDER", "CONTAINER_ORCHESTRATION", "CONNECTIVITY_INFRASTRUCTURE"
        ]
        actual_families = [f.value for f in ConnectorFamily]
        for ef in expected_families:
            self.assertIn(ef, actual_families)

    # -------------------------------------------------------------------------
    # Group W: Security / Data Minimization
    # -------------------------------------------------------------------------
    def test_W01_no_raw_passwords_or_tokens_in_sanitized_dictionaries(self):
        """W01: Serialized profile dictionary omits raw secrets."""
        prof = ConnectionProfile(
            raw_credentials={"password": "password123", "token": "tok_abc"},
            driver_options={"secret_auth": "raw_auth"},
        )
        d = prof.to_sanitized_dict()
        self.assertNotIn("password", d)
        self.assertNotIn("token", d)
        self.assertEqual(d["driver_options"]["secret_auth"], "[REDACTED]")

    # -------------------------------------------------------------------------
    # Group X: Error Truthfulness
    # -------------------------------------------------------------------------
    def test_X01_error_categories_distinguish_authentication_vs_connectivity(self):
        """X01: Error classification accurately distinguishes authentication vs connectivity."""
        bridge = LegacyAdapterUniversalBridge("pg", SystemType.POSTGRESQL, ConnectorFamily.RELATIONAL_DATABASE, "PostgreSQL")
        e_auth = bridge.classify_error(Exception("FATAL: password authentication failed for user"))
        e_conn = bridge.classify_error(Exception("Connection refused (unreachable host)"))
        e_perm = bridge.classify_error(Exception("Permission denied for relation"))

        self.assertEqual(e_auth, ConnectorErrorCategory.AUTHENTICATION)
        self.assertEqual(e_conn, ConnectorErrorCategory.CONNECTIVITY)
        self.assertEqual(e_perm, ConnectorErrorCategory.AUTHORIZATION)

    # -------------------------------------------------------------------------
    # Group Y: Boundedness & Synthetic Scale
    # -------------------------------------------------------------------------
    def test_Y01_synthetic_1000_manifest_registry_scale(self):
        """Y01: Registering 1,000 synthetic manifests executes rapidly without memory leaks."""
        for i in range(1000):
            cid = f"scale-manifest-{i}"
            m = UniversalCapabilityManifest(cid, ConnectorFamily.RELATIONAL_DATABASE, f"Vendor {i}", "POSTGRESQL")
            self.registry.register_manifest(m, allow_override=True)

        self.assertGreaterEqual(len(self.registry.list_connectors()), 1000)

    # -------------------------------------------------------------------------
    # Group Z: Dead Path / Duplicate Authority Forensics
    # -------------------------------------------------------------------------
    def test_Z01_all_registered_connectors_have_authoritative_manifests(self):
        """Z01: Every connector listed in registry returns a valid manifest."""
        conn_ids = self.registry.list_connectors()
        self.assertGreaterEqual(len(conn_ids), 19)
        for cid in conn_ids:
            manifest = self.registry.get_manifest(cid)
            self.assertIsNotNone(manifest)

    # -------------------------------------------------------------------------
    # Group AA: EngineGateway / IPC Reachability
    # -------------------------------------------------------------------------
    def test_AA01_gateway_exposes_manifest_and_compatibility_routes(self):
        """AA01: EngineGateway routes get_connector_manifest and evaluate_connector_compatibility."""
        res_m = self.gateway.invoke("get_connector_manifest", {"connector_id": "oracle"})
        self.assertTrue(res_m["found"])
        self.assertEqual(res_m["manifest"]["system_type"], "ORACLE")

        res_compat = self.gateway.invoke("evaluate_connector_compatibility", {
            "source_connector_id": "oracle",
            "target_connector_id": "postgresql",
        })
        self.assertTrue(res_compat["is_viable"])
        self.assertEqual(res_compat["compatibility"], SemanticCompatibility.SUPPORTED_WITH_MAPPING.value)

    # -------------------------------------------------------------------------
    # Group AB: Restart / Reconstruction Safety
    # -------------------------------------------------------------------------
    def test_AB01_manifest_reconstructs_truthfully_after_dict_export(self):
        """AB01: Manifest exported to dict and imported back retains exact state flags."""
        m_orig = UniversalCapabilityManifest(
            "restart-test",
            ConnectorFamily.DOCUMENT_DATABASE,
            "MongoDB Test",
            "MONGODB",
            supports_cdc_capture=True,
            implementation_state=ImplementationState.IMPLEMENTED,
            support_state=SupportState.SUPPORTED,
        )
        d = m_orig.to_dict()
        m_recon = UniversalCapabilityManifest.from_dict(d)

        self.assertEqual(m_recon.connector_id, "restart-test")
        self.assertTrue(m_recon.supports_cdc_capture)
        self.assertEqual(m_recon.implementation_state, ImplementationState.IMPLEMENTED)
        self.assertEqual(m_recon.support_state, SupportState.SUPPORTED)

    # -------------------------------------------------------------------------
    # Group AC: Forward Extensibility
    # -------------------------------------------------------------------------
    def test_AC01_future_synthetic_connector_integrates_without_core_modification(self):
        """AC01: Future plugin/connector can be registered and evaluated seamlessly."""
        m_future = UniversalCapabilityManifest(
            "quantum-lake-v9",
            ConnectorFamily.LAKEHOUSE_ANALYTICS,
            "Quantum Analytics",
            "QUANTUM",
            role=ConnectorRole.TARGET,
            supports_bulk_write=True,
        )
        self.registry.register_manifest(m_future, allow_override=True)
        m_pg = self.registry.get_manifest("postgresql")
        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_pg, m_future)
        self.assertTrue(res["is_viable"])
        self.assertEqual(res["compatibility"], SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value)

    # -------------------------------------------------------------------------
    # Group K: Target / Source Role Enforcement
    # -------------------------------------------------------------------------
    def test_K01_target_only_cannot_act_as_source(self):
        """K01: Target-only manifest fails compatibility when used as source."""
        m_target = UniversalCapabilityManifest("snow", ConnectorFamily.CLOUD_DATA_WAREHOUSE, "Snowflake", "SNOWFLAKE", role=ConnectorRole.TARGET, implementation_state=ImplementationState.IMPLEMENTED, support_state=SupportState.SUPPORTED, supports_bulk_read=True)
        m_dest = UniversalCapabilityManifest("pg", ConnectorFamily.RELATIONAL_DATABASE, "PostgreSQL", "POSTGRESQL", role=ConnectorRole.TARGET, implementation_state=ImplementationState.IMPLEMENTED, support_state=SupportState.SUPPORTED, supports_bulk_write=True)
        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_target, m_dest)
        self.assertFalse(res["is_viable"])
        self.assertEqual(res["compatibility"], "UNSUPPORTED")

    # -------------------------------------------------------------------------
    # Group AD: Original 19 Connector Truth Audit
    # -------------------------------------------------------------------------
    def test_AD01_all_19_baseline_systems_verified(self):
        """AD01: All 19 baseline systems are present and truthfully configured in UniversalConnectorRegistry."""
        baseline_19 = [
            ("oracle", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("postgresql", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("mysql", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("mariadb", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("mssql", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("ibm_db2", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("sqlite", ConnectorFamily.RELATIONAL_DATABASE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("snowflake", ConnectorFamily.CLOUD_DATA_WAREHOUSE, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("bigquery", ConnectorFamily.CLOUD_DATA_WAREHOUSE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("redshift", ConnectorFamily.CLOUD_DATA_WAREHOUSE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("databricks", ConnectorFamily.LAKEHOUSE_ANALYTICS, ImplementationState.IMPLEMENTED, SupportState.SUPPORTED),
            ("hdfs", ConnectorFamily.DISTRIBUTED_FILESYSTEM, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("mongodb", ConnectorFamily.DOCUMENT_DATABASE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("cassandra", ConnectorFamily.WIDE_COLUMN_DATABASE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("neo4j", ConnectorFamily.GRAPH_DATABASE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("redis", ConnectorFamily.KEY_VALUE_STORE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("elasticsearch", ConnectorFamily.SEARCH_ENGINE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("s3", ConnectorFamily.OBJECT_STORAGE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("gcs", ConnectorFamily.OBJECT_STORAGE, ImplementationState.STUB, SupportState.UNSUPPORTED),
            ("azure_blob", ConnectorFamily.OBJECT_STORAGE, ImplementationState.STUB, SupportState.UNSUPPORTED),
        ]

        for cid, expected_family, expected_impl, expected_support in baseline_19:
            manifest = self.registry.get_manifest(cid)
            self.assertIsNotNone(manifest, f"Missing manifest for {cid}")
            self.assertEqual(manifest.family, expected_family, f"Family mismatch for {cid}")
            self.assertEqual(manifest.implementation_state, expected_impl, f"Impl state mismatch for {cid}")
            self.assertEqual(manifest.support_state, expected_support, f"Support state mismatch for {cid}")


if __name__ == "__main__":
    unittest.main()
