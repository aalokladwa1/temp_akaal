"""
AKAAL P4.3 — Cloud Data Warehouse & Lakehouse Fleet Hostile Reality Suite.
==========================================================================
Hostile reality verification of Snowflake, BigQuery, Redshift, and Databricks.
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
    """Hostile reality test suite for P4.3 warehouse and lakehouse adapters."""

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

    def test_03_missing_drivers_fail_closed(self):
        """03: Connect attempts with missing drivers or invalid endpoints fail closed."""
        async def run():
            # Snowflake empty host
            sf = SnowflakeAdapter(self._make_cfg(SystemType.SNOWFLAKE, host=""))
            with self.assertRaises(RuntimeError):
                await sf.connect()

            # BigQuery empty project_id
            bq = BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host=""))
            with self.assertRaises(RuntimeError):
                await bq.connect()

            # Redshift empty host
            rs = RedshiftAdapter(self._make_cfg(SystemType.REDSHIFT, host=""))
            with self.assertRaises(RuntimeError):
                await rs.connect()

            # Databricks empty server_hostname
            db = DatabricksAdapter(self._make_cfg(SystemType.DATABRICKS, host=""))
            with self.assertRaises(RuntimeError):
                await db.connect()

        self.loop.run_until_complete(run())

    def test_04_zero_mock_mode_in_production_paths(self):
        """04: Production adapter instances must contain ZERO mock_mode attributes."""
        sf = SnowflakeAdapter(self._make_cfg(SystemType.SNOWFLAKE, host="account"))
        bq = BigQueryAdapter(self._make_cfg(SystemType.BIGQUERY, host="proj"))
        rs = RedshiftAdapter(self._make_cfg(SystemType.REDSHIFT, host="host"))
        db = DatabricksAdapter(self._make_cfg(SystemType.DATABRICKS, host="host"))

        for ad in [sf, bq, rs, db]:
            self.assertFalse(hasattr(ad, "mock_mode"))

    def test_05_staged_transfer_descriptor_and_coordinator(self):
        """05: StagedTransferDescriptor generates deterministic URIs and coordinator cleans artifacts."""
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
                encryption_kms_key="arn:aws:kms:us-east-1:123:key/abc",
            )

            key = desc.generate_stage_key("CUSTOMER_DIM", batch_id="b1")
            self.assertTrue("CUSTOMER_DIM" in key)
            self.assertTrue("batch_b1.parquet" in key)

            uri = desc.generate_stage_uri(key)
            self.assertTrue(uri.startswith("s3://my-stage-bucket/"))

            sanitized = desc.to_sanitized_dict()
            self.assertEqual(sanitized["encryption_kms_key"], "[REDACTED]")

            coordinator = StagedTransferCoordinator()
            staged_uri, count = await coordinator.stage_data_payload(desc, "CUSTOMER_DIM", [{"id": 1}, {"id": 2}], batch_id="b1")
            self.assertEqual(count, 2)
            self.assertEqual(staged_uri, uri)

            cleaned = await coordinator.cleanup_staged_artifacts()
            self.assertEqual(cleaned, 1)

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
