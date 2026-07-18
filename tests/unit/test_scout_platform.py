"""
Unit Tests for Scout Platform Subsystem (Phase 9 - Features 1 to 8 Enterprise Refinements)
===========================================================================================
"""

import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.base_adapter import BaseAdapter
from akaal.adapters.providers.base_provider import BaseDiscoveryProvider
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider
from akaal.adapters.providers.postgres_provider import PostgresDiscoveryProvider
from akaal.adapters.providers.mysql_provider import MySQLDiscoveryProvider
from akaal.adapters.providers.oracle_provider import OracleDiscoveryProvider

from akaal.scout.models.discovery_policy import DiscoveryPolicy, DiscoveryProfile
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.capability_inventory import CapabilityInventory, CapabilityConfidence
from akaal.scout.models.schema_inventory import SchemaInventory, TableMetadata
from akaal.scout.models.object_inventory import ObjectInventory
from akaal.scout.models.storage_inventory import StorageInventory
from akaal.scout.models.discovery_audit import DiscoveryAudit
from akaal.scout.models.cost_estimate import DiscoveryCostEstimate
from akaal.scout.models.permission_assessment import PermissionAssessment, PermissionStatus
from akaal.scout.models.discovery_health import DiscoveryHealth, DiscoveryRecommendation
from akaal.scout.models.discovery_manifest import DiscoveryManifest
from akaal.scout.models.discovery_report import DiscoveryReport

from akaal.scout.events.discovery_events import (
    DiscoveryEventBus,
    DiscoveryStarted,
    StageStarted,
    StageCompleted,
    StageFailed,
    DiscoveryCompleted,
)
from akaal.scout.cache.memory_cache import InMemoryDiscoveryCache
from akaal.scout.metrics.scout_metrics import ScoutMetrics
from akaal.scout.plugins.provider_registry import DiscoveryProviderRegistry
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler

from akaal.scout.pipeline.base_stage import BaseDiscoveryStage
from akaal.scout.pipeline.dependency_graph import StageDependencyGraph
from akaal.scout.pipeline.pipeline_executor import PipelineExecutor
from akaal.scout.pipeline.engine_stage import EngineDetectionStage
from akaal.scout.pipeline.version_stage import VersionDetectionStage
from akaal.scout.pipeline.capability_stage import CapabilityDetectionStage
from akaal.scout.pipeline.instance_stage import InstanceDiscoveryStage
from akaal.scout.pipeline.cluster_stage import ClusterDiscoveryStage
from akaal.scout.pipeline.schema_stage import SchemaDiscoveryStage
from akaal.scout.pipeline.object_stage import ObjectDiscoveryStage
from akaal.scout.pipeline.storage_stage import StorageDiscoveryStage
from akaal.scout.pipeline.fingerprint_stage import FingerprintGenerationStage

from akaal.scout.orchestrator.discovery_orchestrator import DiscoveryOrchestrator
from akaal.scout.api.scout_platform import ScoutPlatform, discover


class MockAdapter(BaseAdapter):
    """Mock Adapter for unit testing Scout."""
    SYSTEM_TYPE = SystemType.POSTGRESQL

    async def connect(self) -> None:
        self.is_connected = True

    async def close(self) -> None:
        self.is_connected = False

    async def check_permissions(self) -> bool:
        return True

    async def discover_tables(self) -> list:
        return ["users", "orders"]

    async def discover_columns(self, table_name: str) -> list:
        return [
            {"name": "id", "data_type": "integer", "primary_key": True},
            {"name": "name", "data_type": "varchar", "primary_key": False},
        ]

    async def discover_foreign_keys(self) -> list:
        return [{"fk_name": "fk_orders_user", "constrained_table": "orders", "referred_table": "users"}]

    async def discover_indexes(self, table_name: str) -> list:
        return [{"index_name": f"idx_{table_name}_pk", "columns": ["id"]}]

    async def discover_constraints(self, table_name: str) -> list:
        return [{"constraint_name": f"pk_{table_name}", "type": "PRIMARY KEY"}]

    async def discover_triggers(self, table_name: str) -> list:
        return []

    async def discover_views(self) -> list:
        return [{"view_name": "v_user_orders"}]

    async def read_batch(self, table_name: str, offset: int, limit: int, last_processed_primary_key=None, incremental_filter=None):
        return []

    async def write_batch(self, table_name: str, rows: list) -> int:
        return 0

    async def get_row_count(self, table_name: str) -> int:
        return 100

    async def compute_checksum(self, table_name: str) -> str:
        return "mock_checksum"


class FailingStage(BaseDiscoveryStage):
    @property
    def stage_name(self) -> str:
        return "FailingStage"

    @property
    def dependencies(self) -> list:
        return ["EngineDetection"]

    async def execute(self, ctx: DiscoveryContext):
        raise RuntimeError("Simulated stage error")


class TestScoutPlatform(unittest.TestCase):

    def setUp(self):
        self.config = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="source-db.example.com",
            port=5432,
            database_name="test_db",
            credentials_ref="vault://pg_creds",
            read_only=True,
        )

    def test_provider_registry_and_compatibility(self):
        registry = DiscoveryProviderRegistry()
        self.assertTrue(registry.supports(SystemType.POSTGRESQL))
        self.assertTrue(registry.supports(SystemType.MYSQL))
        self.assertTrue(registry.supports(SystemType.ORACLE))

        pg_provider_cls = registry.resolve(SystemType.POSTGRESQL)
        self.assertEqual(pg_provider_cls, PostgresDiscoveryProvider)

        warnings = registry.validate_provider_compatibility(SystemType.POSTGRESQL, "PostgreSQL 15.2")
        self.assertEqual(len(warnings), 0)

    def test_discovery_policy_and_profiles(self):
        quick_policy = DiscoveryPolicy.from_profile(DiscoveryProfile.QUICK)
        self.assertFalse(quick_policy.collect_storage_statistics)
        self.assertEqual(quick_policy.maximum_runtime_seconds, 300)

        self.assertFalse(quick_policy.is_schema_allowed("information_schema"))
        self.assertTrue(quick_policy.is_schema_allowed("public"))
        self.assertFalse(quick_policy.is_table_allowed("temp_orders"))
        self.assertTrue(quick_policy.is_table_allowed("orders"))

    def test_capability_confidence_scoring(self):
        cap_inv = CapabilityInventory()
        cap_inv.set_capability("supports_cdc", True, confidence_score=95, evidence="pg_replication_slots")
        self.assertEqual(cap_inv.supports_cdc, True)
        self.assertEqual(cap_inv.confidence_scores["supports_cdc"].confidence_score, 95)
        self.assertEqual(cap_inv.get_average_confidence(), 95.0)

    def test_discovery_health_and_recommendations(self):
        health = DiscoveryHealth()
        health.recommendations.append(DiscoveryRecommendation(
            category="PERMISSIONS",
            severity="WARNING",
            observation="Missing storage stats permission",
            recommendation_text="Grant SELECT ON pg_statistic",
        ))
        score = health.calculate_overall()
        self.assertEqual(score, 100.0)
        self.assertEqual(len(health.recommendations), 1)

    def test_discovery_manifest_and_checksum(self):
        manifest = DiscoveryManifest(engine="POSTGRESQL", fingerprint="abc123hash")
        report_dict = {"test": 123}
        checksum = manifest.compute_checksum(report_dict)
        self.assertTrue(len(checksum) > 0)
        self.assertEqual(manifest.report_checksum, checksum)

    def test_stage_dependency_graph(self):
        stages = [
            FingerprintGenerationStage(),
            EngineDetectionStage(),
            VersionDetectionStage(),
            CapabilityDetectionStage(),
            InstanceDiscoveryStage(),
            ClusterDiscoveryStage(),
            SchemaDiscoveryStage(),
            ObjectDiscoveryStage(),
            StorageDiscoveryStage(),
        ]
        ordered = StageDependencyGraph.resolve_execution_order(stages)
        ordered_names = [s.stage_name for s in ordered]

        self.assertLess(ordered_names.index("EngineDetection"), ordered_names.index("VersionDetection"))
        self.assertLess(ordered_names.index("EngineDetection"), ordered_names.index("InstanceDiscovery"))
        self.assertEqual(ordered_names[-1], "FingerprintGeneration")

    def test_pipeline_executor_and_partial_failure_recovery(self):
        async def _run():
            ctx = DiscoveryContext(request=DiscoveryRequest(self.config))
            stages = [EngineDetectionStage(), FailingStage()]
            executor = PipelineExecutor(stages)
            diags = await executor.execute_all(ctx)
            self.assertEqual(len(diags), 2)
            self.assertEqual(diags[0].status, "SUCCESS")
            self.assertEqual(diags[1].status, "FAILED")
            self.assertTrue(len(ctx.errors) > 0)
        asyncio.run(_run())

    def test_cache_hit_and_miss(self):
        cache = InMemoryDiscoveryCache()
        key = cache.generate_cache_key(self.config)
        self.assertIsNone(cache.get(key))

        report = DiscoveryReport()
        cache.set(key, report, ttl_seconds=60)
        cached = cache.get(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.schema_version, "1.0.0")

    def test_end_to_end_enterprise_discovery(self):
        async def _run():
            req = DiscoveryRequest(
                connection_config=self.config,
                profile=DiscoveryProfile.STANDARD,
                force_refresh=True,
            )
            report = await ScoutPlatform.discover(req)
            self.assertIsNotNone(report)
            self.assertEqual(report.schema_version, "1.0.0")
            self.assertEqual(report.report_version, "1.0.0")
            self.assertEqual(report.generator_version, "scout-1.0.0")
            self.assertEqual(report.compatibility_version, "1.0.0")
            self.assertIsNotNone(report.fingerprint)
            self.assertTrue(len(report.fingerprint.sha256_hash) > 0)
            self.assertTrue(len(report.sha256_checksum) > 0)

            report_dict = report.to_dict()
            self.assertIn("audit_trail", report_dict)
            self.assertIn("manifest", report_dict)
            self.assertIn("permission_assessment", report_dict)
            self.assertIn("health_assessment", report_dict)
            self.assertIn("cost_estimate", report_dict)

            # Test report checksum consistency
            self.assertTrue(len(report.compute_sha256_checksum()) > 0)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
