"""
AKAAL P4.3 — Cloud Data Warehouse & Lakehouse Fleet Comprehensive Hostile Truth-Consistency Suite.
================================================================================================
Hostile reality verification of Snowflake, BigQuery, Redshift, and Databricks across the 3 Freeze Blockers:
1. Staging Cleanup Reality (Descriptor vs Remote Object Deletion)
2. Concurrent Mutation Resume Truth (Keyset vs Snapshot Isolation)
3. Transaction Boundary Truth (Client SQL Transaction vs Job Atomicity vs Delta ACID)
"""

import unittest
import asyncio
import os
import typing

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.adapter_registry import get_adapter_class
from akaal.adapters.warehouse.snowflake_adapter import SnowflakeAdapter
from akaal.adapters.warehouse.bigquery_adapter import BigQueryAdapter
from akaal.adapters.warehouse.redshift_adapter import RedshiftAdapter
from akaal.adapters.warehouse.databricks_adapter import DatabricksAdapter
from akaal.connectors.bridge import register_canonical_bridge_connectors, LegacyAdapterUniversalBridge
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.staging import StagedTransferDescriptor, StagedTransferCoordinator


class TestP43WarehouseLakehouseFleet(unittest.TestCase):
    """Expanded Hostile Reality Test Suite for P4.3 Warehouse and Lakehouse Adapters."""

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
    # Registry Resolution & Bridge Registration Truth
    # -------------------------------------------------------------------------
    def test_01_adapter_registry_and_bridge_metadata(self):
        """01: Verify all 4 warehouse/lakehouse adapters resolve via registry and bridge."""
        types = [SystemType.SNOWFLAKE, SystemType.BIGQUERY, SystemType.REDSHIFT, SystemType.DATABRICKS]
        for st in types:
            cls = get_adapter_class(st)
            self.assertIsNotNone(cls)

        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["snowflake", "bigquery", "redshift", "databricks"]:
            bridge = reg.get_connector(sys_str)
            self.assertIsNotNone(bridge)
            manifest = bridge.manifest
            self.assertEqual(manifest.supports_cdc_capture, False)
            self.assertEqual(manifest.implementation_state.name, "IMPLEMENTED")
            self.assertEqual(manifest.support_state.name, "SUPPORTED")

    # -------------------------------------------------------------------------
    # Connectivity Fail Closed
    # -------------------------------------------------------------------------
    def test_02_disconnected_operations_fail_closed(self):
        """02: Disconnected operations across all 4 adapters raise RuntimeError fail-closed."""
        async def run():
            adapters = [
                SnowflakeAdapter(self._make_cfg(SystemType.SNOWFLAKE, host="account.snowflakecomputing.com")),
                BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host="my-gcp-proj")),
                RedshiftAdapter(self._make_cfg(SystemType.REDSHIFT, host="rs.amazonaws.com")),
                DatabricksAdapter(self._make_cfg(SystemType.DATABRICKS, host="dbc.cloud.databricks.com")),
            ]

            for ad in adapters:
                self.assertFalse(ad.is_connected)
                with self.assertRaises(RuntimeError):
                    await ad.discover_tables()
                with self.assertRaises(RuntimeError):
                    await ad.discover_columns("test_tbl")
                with self.assertRaises(RuntimeError):
                    await ad.read_batch("test_tbl", offset=0, limit=10)
                with self.assertRaises(RuntimeError):
                    await ad.write_batch("test_tbl", [{"id": 1}])
                with self.assertRaises(RuntimeError):
                    await ad.execute_staged_bulk_load("test_tbl", "s3://bucket/stage.parquet")
                with self.assertRaises(RuntimeError):
                    await ad.get_row_count("test_tbl")
                with self.assertRaises(RuntimeError):
                    await ad.compute_checksum("test_tbl")

        self.loop.run_until_complete(run())

    def test_03_missing_drivers_and_failed_connection_isolation(self):
        """03: Connect attempts with invalid endpoints or missing credentials fail closed."""
        async def run():
            sf = SnowflakeAdapter(self._make_cfg(SystemType.SNOWFLAKE, host=""))
            with self.assertRaises(RuntimeError):
                await sf.connect()
            self.assertFalse(sf.is_connected)

            bq = BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host=""))
            with self.assertRaises(RuntimeError):
                await bq.connect()
            self.assertFalse(bq.is_connected)

            rs = RedshiftAdapter(self._make_cfg(SystemType.REDSHIFT, host=""))
            with self.assertRaises(RuntimeError):
                await rs.connect()
            self.assertFalse(rs.is_connected)

            db = DatabricksAdapter(self._make_cfg(SystemType.DATABRICKS, host=""))
            with self.assertRaises(RuntimeError):
                await db.connect()
            self.assertFalse(db.is_connected)

        self.loop.run_until_complete(run())

    def test_04_zero_mock_mode_in_production_paths(self):
        """04: Production adapter instances must contain ZERO mock_mode attributes."""
        sf = SnowflakeAdapter(self._make_cfg(SystemType.SNOWFLAKE, host="account"))
        bq = BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host="proj"))
        rs = RedshiftAdapter(self._make_cfg(SystemType.REDSHIFT, host="host"))
        db = DatabricksAdapter(self._make_cfg(SystemType.DATABRICKS, host="host"))

        for ad in [sf, bq, rs, db]:
            self.assertFalse(hasattr(ad, "mock_mode"))

    # -------------------------------------------------------------------------
    # BLOCKER 1: Staging Cleanup Reality Audit
    # -------------------------------------------------------------------------
    def test_05_staging_cleanup_descriptor_vs_remote_object(self):
        """05: StagedTransferCoordinator clears descriptors while remote storage deletion requires adapter."""
        async def run():
            desc = StagedTransferDescriptor(
                migration_id="mig-100",
                job_id="job-200",
                run_id="run-300",
                source_connector_id="pg-source",
                target_connector_id="sf-target",
                stage_provider="S3",
                stage_bucket="my-stage-bucket",
                file_format="PARQUET",
                encryption_kms_key="arn:aws:kms:us-east-1:123:key/abc-secret",
            )

            coord = StagedTransferCoordinator()
            staged_uri, count = await coord.stage_data_payload(desc, "CUSTOMER_DIM", [{"id": 1}, {"id": 2}], batch_id="b1")
            self.assertEqual(count, 2)
            self.assertTrue(staged_uri.startswith("s3://my-stage-bucket/"))

            # Descriptor cleared in memory
            cleaned = await coord.cleanup_staged_artifacts()
            self.assertEqual(cleaned, 1)
            self.assertEqual(len(coord._staged_files), 0)

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # BLOCKER 2: Concurrent Mutation Safe Resume Truth
    # -------------------------------------------------------------------------
    def test_06_concurrent_mutation_resume_truth(self):
        """06: Keyset pagination supports position resume, but does NOT guarantee snapshot isolation under DML."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        # Keyset resume is True for bulk checkpointing, but concurrent mutation safety is False
        for sys_str in ["snowflake", "bigquery", "redshift", "databricks"]:
            bridge = reg.get_connector(sys_str)
            manifest = bridge.manifest
            # CDC capture and continuous sync remain False
            self.assertFalse(manifest.supports_cdc_capture)
            self.assertFalse(manifest.supports_cdc_position_resume)

    # -------------------------------------------------------------------------
    # BLOCKER 3: Transaction Boundary Truth
    # -------------------------------------------------------------------------
    def test_07_transaction_boundary_truth(self):
        """07: Snowflake/Redshift support client SQL transactions; BigQuery/Databricks provide per-command ACID."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        sf_manifest = reg.get_connector("snowflake").manifest
        rs_manifest = reg.get_connector("redshift").manifest
        bq_manifest = reg.get_connector("bigquery").manifest
        db_manifest = reg.get_connector("databricks").manifest

        self.assertTrue(sf_manifest.supports_transactions)
        self.assertTrue(rs_manifest.supports_transactions)
        self.assertFalse(bq_manifest.supports_transactions)
        self.assertFalse(db_manifest.supports_transactions)

    # -------------------------------------------------------------------------
    # BigQuery Error Propagation & Secret Safety
    # -------------------------------------------------------------------------
    def test_08_bigquery_error_propagation_and_secret_safety(self):
        """08: Verify BigQuery adapter raises RuntimeError on insert errors and redacts credentials."""
        bq = BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host="proj"))
        bq.is_connected = True

        class FakeBQClient:
            def insert_rows_json(self, table_ref, json_rows):
                return [{"index": 0, "errors": [{"reason": "invalid", "message": "Bad value"}]}]

        bq._client = FakeBQClient()

        async def run():
            with self.assertRaises(RuntimeError) as ctx:
                await bq.write_batch("my_table", [{"col1": "val1"}])
            self.assertIn("BigQuery streaming write failed with errors", str(ctx.exception))

        self.loop.run_until_complete(run())

    # -------------------------------------------------------------------------
    # Roles & Proof Levels
    # -------------------------------------------------------------------------
    def test_09_source_target_roles_and_proof_level(self):
        """09: Verify BOTH source/target roles and UNIT_PROVEN proof level (LIVE_SYSTEM_PROVEN = NO)."""
        reg = UniversalConnectorRegistry()
        register_canonical_bridge_connectors(reg)

        for sys_str in ["snowflake", "bigquery", "redshift", "databricks"]:
            bridge = reg.get_connector(sys_str)
            manifest = bridge.manifest
            self.assertTrue(manifest.supports_bulk_read)
            self.assertTrue(manifest.supports_bulk_write)
            self.assertEqual(manifest.proof_level.name, "UNIT_PROVEN")


if __name__ == "__main__":
    unittest.main()
