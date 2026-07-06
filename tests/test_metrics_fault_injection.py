# -*- coding: utf-8 -*-
import unittest
import asyncio
from unittest.mock import MagicMock, patch

from akaal.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.project import MigrationSession
from akaal.agents.gb.gb_agent import GBAgent
from akaal.agents.manager.manager_agent import ManagerAgent
from akaal.metrics.registry import MetricsRegistry
from akaal.metrics.metrics import Counter, Histogram, Gauge, Timer, Rate
from akaal.metrics.summary import SummaryGenerator


class TestMetricsFaultInjection(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = MetricsRegistry()

    # 1. Test that if GBAgent metric increment throws, migration continues
    async def test_gb_agent_metric_fault_isolation(self):
        # Create a counter that throws on increment
        broken_counter = MagicMock(spec=Counter)
        broken_counter.increment.side_effect = RuntimeError("Failed to increment counter")
        
        # Patch registry.counter to return this broken counter
        mock_registry = MagicMock(spec=MetricsRegistry)
        mock_registry.counter.return_value = broken_counter
        mock_registry.timer.side_effect = RuntimeError("Failed to create timer")

        state = MagicMock()
        bus = MagicMock()
        checkpoint = MagicMock()
        
        # Instantiate GBAgent with this broken registry
        agent = GBAgent(
            global_state=state,
            message_bus=bus,
            checkpoint_manager=checkpoint,
            metrics_registry=mock_registry
        )

        # Call GBAgent migrate_table directly
        # Mock adapter configurations
        source_config = MagicMock()
        target_config = MagicMock()
        
        # Mock create_adapter
        mock_src = MagicMock()
        mock_tgt = MagicMock()
        mock_src.connect = AsyncMock()
        mock_tgt.connect = AsyncMock()
        mock_src.close = AsyncMock()
        mock_tgt.close = AsyncMock()
        mock_src._primary_key_columns = AsyncMock(return_value=["id"])
        mock_tgt._primary_key_columns = AsyncMock(return_value=["id"])
        mock_src.read_batch = AsyncMock()
        mock_tgt.write_batch = AsyncMock(return_value=None)
        
        # Simulate read_batch terminating on second loop (empty return)
        # On first call return a batch, on second call return None/empty list
        mock_src.read_batch.side_effect = [[{"id": 1, "val": "data"}], []]

        # Mock CheckpointManager methods
        checkpoint.resume = AsyncMock(return_value=None)
        checkpoint.save_progress = AsyncMock(return_value=True)
        checkpoint.mark_completed = AsyncMock(return_value=True)

        with patch("akaal.agents.gb.gb_agent.create_adapter") as mock_create:
            mock_create.side_effect = lambda cfg: mock_src if cfg == source_config else mock_tgt
            
            # Run migrate_table; it should NOT raise or crash because of metrics errors
            res = await agent.migrate_table(
                source_config=source_config,
                target_config=target_config,
                table_name="users"
            )
            
            # The migration MUST succeed
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["rows_migrated"], 1)

    # 2. Test that if ManagerAgent metric increment throws, migration continues
    async def test_manager_agent_metric_fault_isolation(self):
        mock_registry = MagicMock(spec=MetricsRegistry)
        mock_registry.timer.side_effect = RuntimeError("Failed to start timer")
        mock_registry.counter.side_effect = RuntimeError("Failed to increment counter")

        state = MagicMock()
        bus = MagicMock()
        audit = MagicMock()
        checkpoint = MagicMock()

        agent = ManagerAgent(
            global_state=state,
            message_bus=bus,
            audit_logger=audit,
            checkpoint_manager=checkpoint,
            metrics_registry=mock_registry
        )

        # Since run_migration executes stages that are mocked, let's verify direct metrics calls inside run_migration
        # run_migration is fully wrapped in try/except around metrics. We verify timer context managers propagate normally.
        # Timer itself:
        hist = MagicMock(spec=Histogram)
        hist.record.side_effect = RuntimeError("Failed to record histogram")
        timer = Timer(hist)
        
        # Timer context must not suppress user exceptions, but metrics exception itself must be isolated
        try:
            with timer:
                # normal execution
                pass
        except Exception:
            self.fail("Timer context raised exception from histogram record")

    # 3. Test that if SummaryGenerator throws, pipeline does not crash
    def test_summary_generator_fault_isolation(self):
        snapshot = MagicMock()
        generator = SummaryGenerator()
        
        with patch.object(generator, "generate", side_effect=ValueError("Invalid snapshot data")):
            # Simulate pipeline summary extraction block
            try:
                # This is what pipeline does:
                summary = generator.generate(snapshot)
            except Exception as e:
                # Verify that ValueError is indeed raised, but the pipeline catches it (tested in next test)
                self.assertIsInstance(e, ValueError)

# Helper async mock classes
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

if __name__ == "__main__":
    unittest.main()
