"""
Akaal — Discovery Orchestrator
=============================
Engine-agnostic orchestrator managing DiscoveryContext, PipelineExecutor, Cache, and Events.
"""

import time
import asyncio
import logging
from typing import Optional

from akaal.adapters.adapter_registry import create_adapter
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.scout.plugins.provider_registry import DiscoveryProviderRegistry
from akaal.scout.cache.base_cache import BaseDiscoveryCache
from akaal.scout.cache.memory_cache import InMemoryDiscoveryCache
from akaal.scout.metrics.scout_metrics import ScoutMetrics
from akaal.scout.events.discovery_events import DiscoveryEventBus, DiscoveryStarted, DiscoveryCompleted
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler
from akaal.scout.pipeline import (
    PipelineExecutor,
    EngineDetectionStage,
    VersionDetectionStage,
    CapabilityDetectionStage,
    InstanceDiscoveryStage,
    ClusterDiscoveryStage,
    SchemaDiscoveryStage,
    ObjectDiscoveryStage,
    StorageDiscoveryStage,
    FingerprintGenerationStage,
)

logger = logging.getLogger("akaal.scout.orchestrator")


class DiscoveryOrchestrator:
    """Engine-agnostic Discovery Orchestrator."""

    def __init__(
        self,
        registry: Optional[DiscoveryProviderRegistry] = None,
        cache: Optional[BaseDiscoveryCache] = None,
        event_bus: Optional[DiscoveryEventBus] = None,
    ) -> None:
        self.registry = registry or DiscoveryProviderRegistry()
        self.cache = cache or InMemoryDiscoveryCache()
        self.event_bus = event_bus or DiscoveryEventBus()

    async def execute_discovery(self, request: DiscoveryRequest) -> DiscoveryReport:
        metrics = ScoutMetrics()
        cache_key = self.cache.generate_cache_key(request.connection_config)

        # Check Cache if not force_refresh
        if not request.force_refresh:
            cached_report = self.cache.get(cache_key)
            if cached_report is not None:
                metrics.record_cache_hit()
                logger.info("[ScoutOrchestrator] Cache HIT for key=%s", cache_key)
                return cached_report

        metrics.record_cache_miss()
        logger.info("[ScoutOrchestrator] Cache MISS. Starting source discovery...")

        self.event_bus.publish(DiscoveryStarted({
            "system_type": str(request.connection_config.system_type),
            "host": request.connection_config.host,
            "database_name": request.connection_config.database_name,
        }))

        # Resolve Adapter and DiscoveryProvider
        adapter = create_adapter(request.connection_config)
        provider_cls = self.registry.resolve(request.connection_config.system_type)
        provider = provider_cls(adapter)

        # Create Runtime Context
        ctx = DiscoveryContext(
            request=request,
            provider=provider,
            event_bus=self.event_bus,
            metrics=metrics,
            logger=logger,
        )

        ctx.start_time = time.time()

        # Connect adapter & verify read-only safety
        try:
            await adapter.connect()
            read_only_ok = await provider.check_read_only_permissions()
            ctx.read_only_verified = read_only_ok
            if not read_only_ok:
                ctx.add_warning("Source adapter credentials could not confirm strict read-only mode.")
        except Exception as conn_exc:
            ctx.add_error(f"Failed to connect to source database: {str(conn_exc)}")

        # Initialize Pipeline Stages
        stages = [
            EngineDetectionStage(),
            VersionDetectionStage(),
            CapabilityDetectionStage(),
            InstanceDiscoveryStage(),
            ClusterDiscoveryStage(),
            SchemaDiscoveryStage(),
            ObjectDiscoveryStage(),
            StorageDiscoveryStage(),
            FingerprintGenerationStage(),
        ]

        executor = PipelineExecutor(stages=stages, timeout_seconds=60.0)

        # Execute Pipeline
        await executor.execute_all(ctx)

        # Close Adapter Connection
        try:
            await adapter.close()
        except Exception:
            pass

        ctx.end_time = time.time()
        metrics.total_duration_ms = (ctx.end_time - ctx.start_time) * 1000.0

        # Assemble Discovery Report
        report = DiscoveryAssembler.assemble(ctx, cache_hit=False)

        # Store in cache
        self.cache.set(cache_key, report, ttl_seconds=request.ttl_seconds)

        self.event_bus.publish(DiscoveryCompleted(
            overall_status=report.health.overall_status,
            total_duration_ms=report.performance.total_discovery_duration_ms,
        ))

        return report
