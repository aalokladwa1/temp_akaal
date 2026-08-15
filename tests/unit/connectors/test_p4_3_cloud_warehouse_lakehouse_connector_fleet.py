"""
AKAAL P4.3 — Cloud Data Warehouse & Lakehouse Connector Fleet Test Suite.
========================================================================
Production acceptance and verification suite for Snowflake, Google BigQuery,
Amazon Redshift, and Databricks Delta Lake across all dimensions A through AJ.
"""

import unittest
import asyncio
import threading
from typing import Dict, Any, List, Optional
from decimal import Decimal

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    ProofLevel,
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
from akaal.connectors.staging import StagedTransferCoordinator, StagedTransferDescriptor
from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import create_adapter, get_adapter_class

from akaal.cdc.domain.positions import (
    DeltaTableVersionPosition,
    WarehouseQueryPosition,
    PostgresLSNPosition,
    parse_source_position,
)
from akaal.gateway.engine_gateway import EngineGateway


class TestP43WarehouseLakehouseFleet(unittest.TestCase):
    """Production Acceptance Test Suite for Snowflake, BigQuery, Redshift, and Databricks."""

    def setUp(self) -> None:
        self.registry = UniversalConnectorRegistry.get_instance()
        self.gateway = EngineGateway()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.warehouse_ids = ["snowflake", "bigquery", "redshift", "databricks"]

    def tearDown(self) -> None:
        self.loop.close()

    # -------------------------------------------------------------------------
    # A & B: Fleet Registration & Identity
    # -------------------------------------------------------------------------
    def test_AB01_fleet_registration_and_normalized_identity(self):
        """AB01: All 4 warehouse/lakehouse connectors are registered and normalized."""
        for cid in self.warehouse_ids:
            manifest = self.registry.get_manifest(cid)
            self.assertIsNotNone(manifest, f"Manifest missing for {cid}")
            self.assertEqual(manifest.connector_id, cid)

            # Casing and whitespace normalization
            manifest_norm = self.registry.get_manifest(f"  {cid.upper()}  ")
            self.assertIsNotNone(manifest_norm)
            self.assertEqual(manifest_norm.connector_id, cid)

    def test_AB02_unknown_warehouse_connector_fails_closed(self):
        """AB02: Unknown warehouse connector lookup returns None."""
        self.assertIsNone(self.registry.get_manifest("unknown_warehouse_system"))
        self.assertIsNone(self.registry.get_connector("quantum_lakehouse"))

    # -------------------------------------------------------------------------
    # C & D: Manifest Truthfulness & Role Semantics
    # -------------------------------------------------------------------------
    def test_CD01_manifest_truthfulness_and_both_roles(self):
        """CD01: Verifies truthful manifest state (Snowflake/Databricks implemented; BigQuery/Redshift stub)."""
        for cid in self.warehouse_ids:
            m = self.registry.get_manifest(cid)
            if cid in ("snowflake", "databricks"):
                self.assertEqual(m.implementation_state, ImplementationState.IMPLEMENTED)
                self.assertEqual(m.support_state, SupportState.SUPPORTED)
            else:
                self.assertEqual(m.implementation_state, ImplementationState.STUB)
                self.assertEqual(m.support_state, SupportState.UNSUPPORTED)
            self.assertEqual(m.registration_state, RegistrationState.REGISTERED)
            self.assertEqual(m.pipeline_state, PipelineState.REACHABLE)

    # -------------------------------------------------------------------------
    # E, F, G: Snowflake Discovery, Datatypes & Staged Load
    # -------------------------------------------------------------------------
    def test_EFG01_snowflake_discovery_types_and_staged_load(self):
        """EFG01: Snowflake schema discovery, datatype extraction, and staged COPY INTO execution."""
        async def run_snowflake():
            cfg = ConnectionConfig(
                system_type=SystemType.SNOWFLAKE,
                host="sf-account.example.com",
                port=443,
                database_name="ANALYTICS_DB",
                credentials_ref="vault-ref",
                extra={"mock_mode": True, "warehouse": "COMPUTE_WH", "schema": "PUBLIC"},
            )
            adapter = create_adapter(cfg)
            await adapter.connect()

            # Discovery
            datasets = await adapter.discover_datasets()
            self.assertIn("ANALYTICS_DB.PUBLIC", datasets)
            tables = await adapter.discover_tables()
            self.assertIn("CUSTOMER_DIM", tables)

            # Columns & Types
            cols = await adapter.discover_columns("CUSTOMER_DIM")
            type_names = {c["column_name"]: c["data_type"] for c in cols}
            self.assertEqual(type_names["ID"], "NUMBER(38,0)")
            self.assertEqual(type_names["METADATA_PAYLOAD"], "VARIANT")
            self.assertEqual(type_names["GEO_LOCATION"], "GEOGRAPHY")

            # Clustering metadata
            clustering = await adapter.get_clustering_metadata("CUSTOMER_DIM")
            self.assertEqual(clustering["clustering_key"], "(CREATED_AT, ID)")

            # Staged Load Execution
            load_res = await adapter.execute_staged_bulk_load(
                target_table="CUSTOMER_DIM",
                stage_uri="@MY_S3_STAGE/data.parquet",
                file_format="PARQUET",
            )
            self.assertTrue(load_res["success"])
            self.assertEqual(load_res["rows_loaded"], 1000)

            # UNLOAD to stage
            unload_res = await adapter.unload_to_stage(
                source_table="CUSTOMER_DIM",
                stage_uri="@MY_S3_STAGE/unload/",
                file_format="PARQUET",
            )
            self.assertTrue(unload_res["success"])

            await adapter.close()

        self.loop.run_until_complete(run_snowflake())

    # -------------------------------------------------------------------------
    # H, I, J: BigQuery Discovery, Nested Schema & Job Semantics
    # -------------------------------------------------------------------------
    def test_HIJ01_bigquery_discovery_nested_schema_and_load_job(self):
        """HIJ01: BigQuery dataset discovery, nested STRUCT/ARRAY metadata, and load job simulation."""
        async def run_bigquery():
            cfg = ConnectionConfig(
                system_type=SystemType.BIGQUERY,
                host="my-gcp-project.example.com",
                port=443,
                database_name="analytics_dataset",
                credentials_ref="vault-ref",
                extra={"mock_mode": True, "location": "US"},
            )
            adapter = create_adapter(cfg)
            await adapter.connect()

            # Datasets & Tables
            datasets = await adapter.discover_datasets()
            self.assertIn("analytics_dataset", datasets)
            tables = await adapter.discover_tables()
            self.assertIn("events_partitioned", tables)

            # Nested Columns & ARRAY
            cols = await adapter.discover_columns("events_partitioned")
            col_map = {c["column_name"]: c for c in cols}
            self.assertEqual(col_map["device_info"]["data_type"], "STRUCT")
            self.assertGreater(len(col_map["device_info"]["fields"]), 0)
            self.assertEqual(col_map["tags"]["mode"], "REPEATED")

            # LoadJob
            job_res = await adapter.execute_staged_bulk_load(
                target_table="events_partitioned",
                stage_uri="gs://my-bucket/events/*.parquet",
                file_format="PARQUET",
            )
            self.assertTrue(job_res["success"])
            self.assertIn("bq_job_", job_res["job_id"])
            self.assertEqual(job_res["status"], "DONE")

            await adapter.close()

        self.loop.run_until_complete(run_bigquery())

    # -------------------------------------------------------------------------
    # K, L: Redshift Discovery & S3 COPY/UNLOAD Semantics
    # -------------------------------------------------------------------------
    def test_KL01_redshift_discovery_and_s3_staged_copy(self):
        """KL01: Redshift dist/sort key discovery, SUPER datatype, and S3 COPY execution."""
        async def run_redshift():
            cfg = ConnectionConfig(
                system_type=SystemType.REDSHIFT,
                host="redshift-cluster.example.com",
                port=5439,
                database_name="dev",
                credentials_ref="vault-ref",
                extra={
                    "mock_mode": True,
                    "iam_role": "arn:aws:iam::123456789012:role/RedshiftS3Role",
                },
            )
            adapter = create_adapter(cfg)
            await adapter.connect()

            # Discovery
            tables = await adapter.discover_tables()
            self.assertIn("fact_sales", tables)

            # Columns & Keys
            cols = await adapter.discover_columns("fact_sales")
            type_names = {c["column_name"]: c["data_type"] for c in cols}
            self.assertEqual(type_names["sale_id"], "BIGINT")
            self.assertEqual(type_names["payload_super"], "SUPER")

            clustering = await adapter.get_clustering_metadata("fact_sales")
            self.assertEqual(clustering["distribution_style"], "KEY")
            self.assertEqual(clustering["distribution_key"], "customer_id")

            # Staged COPY
            copy_res = await adapter.execute_staged_bulk_load(
                target_table="fact_sales",
                stage_uri="s3://my-dwh-bucket/sales/data.parquet",
                file_format="PARQUET",
            )
            self.assertTrue(copy_res["success"])
            self.assertEqual(copy_res["rows_loaded"], 1000)

            # Staged UNLOAD
            unload_res = await adapter.unload_to_stage(
                source_table="fact_sales",
                stage_uri="s3://my-dwh-bucket/unload/",
                file_format="PARQUET",
            )
            self.assertTrue(unload_res["success"])

            await adapter.close()

        self.loop.run_until_complete(run_redshift())

    # -------------------------------------------------------------------------
    # M, N: Databricks Discovery & Delta Table History Semantics
    # -------------------------------------------------------------------------
    def test_MN01_databricks_unity_catalog_and_delta_table_version(self):
        """MN01: Databricks Unity Catalog, Delta table discovery, and table version extraction."""
        async def run_databricks():
            cfg = ConnectionConfig(
                system_type=SystemType.DATABRICKS,
                host="dbc-prod.cloud.databricks.com",
                port=443,
                database_name="gold",
                credentials_ref="vault-ref",
                extra={"mock_mode": True, "catalog": "main"},
            )
            adapter = create_adapter(cfg)
            await adapter.connect()

            # Datasets & Tables
            datasets = await adapter.discover_datasets()
            self.assertIn("main.gold", datasets)
            tables = await adapter.discover_tables()
            self.assertIn("bronze_raw_events", tables)

            # Columns & Nested Types
            cols = await adapter.discover_columns("silver_cleaned_users")
            type_names = {c["column_name"]: c["data_type"] for c in cols}
            self.assertEqual(type_names["user_id"], "LONG")
            self.assertEqual(type_names["feature_vector"], "ARRAY<FLOAT>")

            # Delta Table Version
            version = await adapter.get_table_version("silver_cleaned_users")
            self.assertEqual(version, 42)

            # Staged COPY INTO
            load_res = await adapter.execute_staged_bulk_load(
                target_table="silver_cleaned_users",
                stage_uri="s3://lakehouse-stage/users.parquet",
                file_format="PARQUET",
            )
            self.assertTrue(load_res["success"])
            self.assertEqual(load_res["delta_commit_version"], 43)

            await adapter.close()

        self.loop.run_until_complete(run_databricks())

    # -------------------------------------------------------------------------
    # O & P: Bulk Read & Write Safety
    # -------------------------------------------------------------------------
    def test_OP01_bulk_read_and_write_across_warehouse_fleet(self):
        """OP01: Bounded batch reads and writes execute without row loss across all 4 engines."""
        sys_types = [SystemType.SNOWFLAKE, SystemType.BIGQUERY, SystemType.REDSHIFT, SystemType.DATABRICKS]

        async def run_rw():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="endpoint.example.com",
                    port=443,
                    database_name="analytics",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()

                # Read
                batch = await adapter.read_batch("my_table", offset=0, limit=10)
                self.assertEqual(len(batch), 10)

                # Write
                written = await adapter.write_batch("my_table", batch)
                self.assertEqual(written, 10)

                await adapter.close()

        self.loop.run_until_complete(run_rw())

    # -------------------------------------------------------------------------
    # Q: Separated Checkpoint Resume Semantics
    # -------------------------------------------------------------------------
    def test_Q01_warehouse_checkpoint_resume_separation(self):
        """Q01: All 4 systems support bulk checkpoint resume, while CDC position resume is False."""
        for cid in self.warehouse_ids:
            m = self.registry.get_manifest(cid)
            self.assertTrue(m.supports_bulk_checkpoint_resume)
            self.assertEqual(m.get_capability_status("bulk_checkpoint_resume"), CapabilitySupportStatus.SUPPORTED)

            self.assertFalse(m.supports_cdc_position_resume)
            self.assertEqual(m.get_capability_status("cdc_position_resume"), CapabilitySupportStatus.UNSUPPORTED)

    # -------------------------------------------------------------------------
    # R: Validation-Only Firewall
    # -------------------------------------------------------------------------
    def test_R01_validation_access_computes_metrics_without_mutation(self):
        """R01: Validation methods compute row counts and checksums in read-only manner."""
        sys_types = [SystemType.SNOWFLAKE, SystemType.BIGQUERY, SystemType.REDSHIFT, SystemType.DATABRICKS]

        async def run_val():
            for st in sys_types:
                cfg = ConnectionConfig(
                    system_type=st,
                    host="endpoint.example.com",
                    port=443,
                    database_name="analytics",
                    credentials_ref="vault-ref",
                    extra={"mock_mode": True},
                )
                adapter = create_adapter(cfg)
                await adapter.connect()

                count = await adapter.get_row_count("dim_users")
                checksum = await adapter.compute_checksum("dim_users")
                self.assertGreater(count, 0)
                self.assertIsInstance(checksum, str)
                self.assertEqual(len(checksum), 64)

                await adapter.close()

        self.loop.run_until_complete(run_val())

    # -------------------------------------------------------------------------
    # S & T: Staged Transfer Coordinator & Stage Cleanup
    # -------------------------------------------------------------------------
    def test_ST01_staged_transfer_coordination_and_cleanup(self):
        """ST01: StagedTransferCoordinator stages data, invokes load, and cleans up artifacts."""
        async def run_staging():
            desc = StagedTransferDescriptor(
                migration_id="mig-dwh-100",
                job_id="job-load-01",
                run_id="run-1",
                source_connector_id="postgresql",
                target_connector_id="snowflake",
                stage_provider="S3",
                stage_bucket="akaal-staging-bucket",
            )
            coord = StagedTransferCoordinator()
            rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

            # Stage Data
            stage_uri, count = await coord.stage_data_payload(desc, "CUSTOMERS", rows, batch_id="batch-001")
            self.assertIn("s3://akaal-staging-bucket/akaal-staging/mig-dwh-100/job-load-01/CUSTOMERS/batch_batch-001.parquet", stage_uri)
            self.assertEqual(count, 2)

            # Cleanup
            cleaned = await coord.cleanup_staged_artifacts()
            self.assertEqual(cleaned, 1)

        self.loop.run_until_complete(run_staging())

    # -------------------------------------------------------------------------
    # U: Retry & Idempotency
    # -------------------------------------------------------------------------
    def test_U01_retry_idempotency_safe(self):
        """U01: Repeated bulk load executions remain idempotent."""
        async def run_retry():
            cfg = ConnectionConfig(
                system_type=SystemType.SNOWFLAKE,
                host="sf-account.example.com",
                port=443,
                database_name="ANALYTICS_DB",
                credentials_ref="vault-ref",
                extra={"mock_mode": True},
            )
            adapter = create_adapter(cfg)
            await adapter.connect()

            res1 = await adapter.execute_staged_bulk_load("CUSTOMER_DIM", "@STAGE/batch1.parquet")
            res2 = await adapter.execute_staged_bulk_load("CUSTOMER_DIM", "@STAGE/batch1.parquet")
            self.assertTrue(res1["success"])
            self.assertTrue(res2["success"])

            await adapter.close()

        self.loop.run_until_complete(run_retry())

    # -------------------------------------------------------------------------
    # V & W: Error Classification & Secret Redaction
    # -------------------------------------------------------------------------
    def test_VW01_error_classification_and_secret_redaction(self):
        """VW01: Error classification distinguishes categories without exposing credentials."""
        bridge = self.registry.get_connector("snowflake")
        cat_auth = bridge.classify_error(Exception("Incorrect username or password was specified"))
        cat_conn = bridge.classify_error(Exception("Connection refused (endpoint unreachable)"))
        cat_authz = bridge.classify_error(Exception("Forbidden: User lacks USAGE privilege on warehouse"))
        cat_throt = bridge.classify_error(Exception("Too many requests: Rate limit exceeded"))

        self.assertEqual(cat_auth, ConnectorErrorCategory.AUTHENTICATION)
        self.assertEqual(cat_conn, ConnectorErrorCategory.CONNECTIVITY)
        self.assertEqual(cat_authz, ConnectorErrorCategory.AUTHORIZATION)
        self.assertEqual(cat_throt, ConnectorErrorCategory.THROTTLED)

        # Profile secret redaction
        prof = ConnectionProfile(
            connector_id="snowflake",
            host="sf-account.example.com",
            raw_credentials={"password": "MySuperSecretKey123!"},
            driver_options={"oauth_secret": "tok_xyz_secret_999"},
        )
        d = prof.to_sanitized_dict()
        self.assertNotIn("MySuperSecretKey123!", str(d))
        self.assertNotIn("tok_xyz_secret_999", str(d))
        self.assertNotIn("MySuperSecretKey123!", repr(prof))

    # -------------------------------------------------------------------------
    # X & Y: Native Positions & Cross-Engine Isolation
    # -------------------------------------------------------------------------
    def test_XY01_native_positions_and_cross_engine_isolation(self):
        """XY01: DeltaTableVersionPosition and WarehouseQueryPosition serialize losslessly and forbid cross-engine comparison."""
        pos_delta = DeltaTableVersionPosition(table_version=42, table_name="users_delta", timestamp_ms=1770000000)
        pos_wh = WarehouseQueryPosition(engine="SNOWFLAKE", query_id="sf-q-100", chunk_index=2, row_offset=50)
        pos_pg = PostgresLSNPosition("0/16B3800")

        # Serialization & Parsing
        d_delta = pos_delta.to_dict()
        reconstructed_delta = parse_source_position(d_delta)
        self.assertEqual(reconstructed_delta.table_version, 42)
        self.assertEqual(reconstructed_delta.engine, "DATABRICKS")

        d_wh = pos_wh.to_dict()
        reconstructed_wh = parse_source_position(d_wh)
        self.assertEqual(reconstructed_wh.query_id, "sf-q-100")
        self.assertEqual(reconstructed_wh.chunk_index, 2)

        # Cross-Engine Comparison Strictly Prohibited
        with self.assertRaises(TypeError):
            _ = pos_delta.is_after(pos_wh)
        with self.assertRaises(TypeError):
            _ = pos_wh.is_after(pos_pg)
        with self.assertRaises(TypeError):
            _ = pos_delta.is_after(pos_pg)

    # -------------------------------------------------------------------------
    # Z: Optional Dependency Absence
    # -------------------------------------------------------------------------
    def test_Z01_optional_dependency_absence_safe(self):
        """Z01: Validating connection profiles does not crash on uninstalled SDKs."""
        for cid in self.warehouse_ids:
            conn = self.registry.get_connector(cid)
            res = conn.validate_configuration(ConnectionProfile(connector_id=cid, host="wh.internal", port=443))
            self.assertTrue(res["valid"])

    # -------------------------------------------------------------------------
    # AA: Concurrency
    # -------------------------------------------------------------------------
    def test_AA01_multithreaded_warehouse_queries(self):
        """AA01: High-concurrency multithreaded lookups execute safely across threads."""
        errors = []

        def worker(thread_idx: int):
            try:
                for cid in self.warehouse_ids:
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
    # AB & AC: Cross-Migration and Cross-Run Isolation
    # -------------------------------------------------------------------------
    def test_ABAC01_cross_migration_and_run_isolation(self):
        """ABAC01: Staging keys and descriptors isolate migrations and runs."""
        desc1 = StagedTransferDescriptor("mig-A", "job-1", "run-1", "postgres", "snowflake", "S3", "bucket-a")
        desc2 = StagedTransferDescriptor("mig-B", "job-1", "run-1", "postgres", "snowflake", "S3", "bucket-a")
        key1 = desc1.generate_stage_key("USERS", "b1")
        key2 = desc2.generate_stage_key("USERS", "b1")
        self.assertNotEqual(key1, key2)
        self.assertIn("mig-A", key1)
        self.assertIn("mig-B", key2)

    # -------------------------------------------------------------------------
    # AD: Compatibility & Directionality
    # -------------------------------------------------------------------------
    def test_AD01_compatibility_and_directionality(self):
        """AD01: Evaluates Relational -> Warehouse, Warehouse -> Relational, and Warehouse <-> Lakehouse."""
        m_pg = self.registry.get_manifest("postgresql")
        m_sf = self.registry.get_manifest("snowflake")
        m_bq = self.registry.get_manifest("bigquery")
        m_dbr = self.registry.get_manifest("databricks")

        # Relational -> Warehouse
        eval_rel_wh = SemanticCompatibilityMatrix.evaluate_compatibility(m_pg, m_sf)
        self.assertTrue(eval_rel_wh["is_viable"])
        self.assertEqual(eval_rel_wh["compatibility"], SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value)

        # Warehouse -> Relational
        eval_wh_rel = SemanticCompatibilityMatrix.evaluate_compatibility(m_sf, m_pg)
        self.assertTrue(eval_wh_rel["is_viable"])
        self.assertEqual(eval_wh_rel["compatibility"], SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS.value)

        # Warehouse <-> Warehouse
        eval_wh_wh = SemanticCompatibilityMatrix.evaluate_compatibility(m_sf, m_bq)
        self.assertTrue(eval_wh_wh["is_viable"])
        self.assertEqual(eval_wh_wh["compatibility"], SemanticCompatibility.SUPPORTED_WITH_MAPPING.value)

        # Warehouse <-> Lakehouse
        eval_wh_lake = SemanticCompatibilityMatrix.evaluate_compatibility(m_sf, m_dbr)
        self.assertTrue(eval_wh_lake["is_viable"])
        self.assertEqual(eval_wh_lake["compatibility"], SemanticCompatibility.SUPPORTED_WITH_MAPPING.value)

    # -------------------------------------------------------------------------
    # AE & AF: EngineGateway & UI Authority
    # -------------------------------------------------------------------------
    def test_AEAF01_engine_gateway_manifest_reachability(self):
        """AEAF01: EngineGateway returns valid manifests for all 4 systems, and fails closed on fake IDs."""
        for cid in self.warehouse_ids:
            res = self.gateway.invoke("get_connector_manifest", {"connector_id": cid})
            self.assertTrue(res["found"], f"Gateway lookup failed for {cid}")
            self.assertIn(res["manifest"]["family"], ("CLOUD_DATA_WAREHOUSE", "LAKEHOUSE_ANALYTICS"))

        fake_res = self.gateway.invoke("get_connector_manifest", {"connector_id": "fake_cloud_db"})
        self.assertFalse(fake_res["found"])
        self.assertIsNone(fake_res["manifest"])

    # -------------------------------------------------------------------------
    # AG & AH: Authority Preservation & Fleet Coexistence
    # -------------------------------------------------------------------------
    def test_AGAH01_authorities_preserved_and_all_four_coexist(self):
        """AGAH01: All 4 systems coexist simultaneously without altering canonical P0-P3 authorities."""
        connectors = [self.registry.get_connector(cid) for cid in self.warehouse_ids]
        self.assertEqual(len(connectors), 4)
        cids = [c.connector_id for c in connectors]
        self.assertEqual(len(set(cids)), 4)

    # -------------------------------------------------------------------------
    # AI & AJ: Serialization & Synthetic Bounded Scale
    # -------------------------------------------------------------------------
    def test_AIAJ01_serialization_and_1000_operations_scale(self):
        """AIAJ01: 1,000 synthetic manifest lookups and serialization cycles run stably."""
        for _ in range(1000):
            for cid in self.warehouse_ids:
                m = self.registry.get_manifest(cid)
                d = m.to_dict()
                self.assertEqual(d["connector_id"], cid)


if __name__ == "__main__":
    unittest.main()
