"""EnterpriseReplicationPlatformV3: Canonical Facade for Phase 11 Platform 3."""

import asyncio
from typing import Any, Dict, List, Optional

# Core Models, Context & Registry
from akaal.replication.core.context import ReplicationContext
from akaal.replication.core.config import ReplicationConfig, ReplicationProfile, FailoverMode
from akaal.replication.core.session import ReplicationSession
from akaal.replication.core.registry import ReplicatorRegistry

# Platform 1 & Platform 2 Integration Facades
from akaal.validation import EnterpriseValidationPlatformV1
from akaal.healing import EnterpriseSelfHealingPlatformV2

# Subsystem Engines (1-5)
from akaal.replication.decision.engine import ReplicationDecisionEngine
from akaal.replication.topology.graph import ReplicationTopologyGraph
from akaal.replication.topology.discovery import TopologyDiscoveryManager
from akaal.replication.sandbox.sandbox import ReplicationSandbox
from akaal.replication.session.manager import ReplicationSessionManager
from akaal.replication.analytics.analytics_engine import AnalyticsEngine

# Services, Router, Failover, Cache, Events, Policy, Distributed
from akaal.replication.routing.router import IntelligentReplicationRouter, AdaptiveStrategySwitcher
from akaal.replication.services.failover import FailoverManager, ReplicationAuditTrailService, ReplicationObservabilityService
from akaal.replication.cache.replication_cache import ReplicationCache
from akaal.replication.events.event_bus import ReplicationEventBus
from akaal.replication.events.publishers import ReplicationEventPublisher
from akaal.replication.policy.engine import ReplicationPolicyEngine
from akaal.replication.distributed.coordinator import DistributedReplicationCoordinator
from akaal.replication.pipeline.orchestrator import ReplicationPipeline

# 6 Domain Replicators
from akaal.replication.domain.core_replication import CoreReplicationDomain
from akaal.replication.domain.conflict_management import ConflictManagementDomain
from akaal.replication.domain.observability_domain import ObservabilityDomain
from akaal.replication.domain.recovery_domain import RecoveryDomain
from akaal.replication.domain.intelligence_domain import IntelligenceDomain
from akaal.replication.domain.governance_domain import GovernanceDomain


class EnterpriseReplicationPlatformV3:
    """Canonical Enterprise Entry Point for all 25 Replication Capabilities."""

    def __init__(
        self,
        config: Optional[ReplicationConfig] = None,
        validation_platform: Optional[EnterpriseValidationPlatformV1] = None,
        self_healing_platform: Optional[EnterpriseSelfHealingPlatformV2] = None,
    ):
        self.config = config or ReplicationConfig()

        # Platform 1 & Platform 2 Facade Integration
        self.validation_platform = validation_platform or EnterpriseValidationPlatformV1()
        self.self_healing_platform = self_healing_platform or EnterpriseSelfHealingPlatformV2()

        # Subsystems 1-5
        self.decision_engine = ReplicationDecisionEngine()
        self.topology_discovery = TopologyDiscoveryManager()
        self.topology_graph = self.topology_discovery.discover_live_topology(self.config.geo_regions)
        self.sandbox_engine = ReplicationSandbox()
        self.session_manager = ReplicationSessionManager()
        self.analytics_engine = AnalyticsEngine()

        # Infrastructure Services & Routing
        self.router = IntelligentReplicationRouter()
        self.strategy_switcher = AdaptiveStrategySwitcher()
        self.failover_manager = FailoverManager()
        self.audit_service = ReplicationAuditTrailService()
        self.observability_service = ReplicationObservabilityService()

        # Cache, Events & Policy
        self.cache = ReplicationCache()
        self.event_bus = ReplicationEventBus()
        self.publisher = ReplicationEventPublisher(self.event_bus)
        self.policy_engine = ReplicationPolicyEngine(profile=self.config.profile, failover_mode=self.config.failover_mode)

        # Distributed Coordinator
        self.distributed_coordinator = DistributedReplicationCoordinator(num_workers=self.config.max_parallel_workers)

        # Replicator Registry & Register 6 Domain Replicators
        self.registry = ReplicatorRegistry()
        self._register_default_domain_replicators()

        # Pipeline Orchestrator
        self.pipeline = ReplicationPipeline(registry=self.registry)

    def _register_default_domain_replicators(self) -> None:
        """Register 6 Domain-Driven Replicators covering all 25 capabilities."""
        self.registry.register_domain_replicator(CoreReplicationDomain())
        self.registry.register_domain_replicator(ConflictManagementDomain())
        self.registry.register_domain_replicator(ObservabilityDomain())
        self.registry.register_domain_replicator(RecoveryDomain())
        self.registry.register_domain_replicator(IntelligenceDomain())
        self.registry.register_domain_replicator(GovernanceDomain())

    def create_context(self, **kwargs) -> ReplicationContext:
        """Construct a ReplicationContext injected with all services and facades."""
        return ReplicationContext(
            config=self.config,
            profile=self.config.profile,
            validation_platform=self.validation_platform,
            self_healing_platform=self.self_healing_platform,
            decision_engine=self.decision_engine,
            topology_graph=self.topology_graph,
            sandbox_engine=self.sandbox_engine,
            session_manager=self.session_manager,
            metrics_engine=self.analytics_engine.metrics_engine,
            router=self.router,
            failover_manager=self.failover_manager,
            policy_engine=self.policy_engine,
            audit_service=self.audit_service,
            observability_service=self.observability_service,
            cache=self.cache,
            event_bus=self.event_bus,
            distributed_coordinator=self.distributed_coordinator,
            runtime_metadata={"replicator_registry": self.registry, **kwargs},
        )

    async def replicate_all_async(self) -> ReplicationSession:
        """Execute replication pipeline across all 6 domain replicators asynchronously."""
        ctx = self.create_context()
        return await self.pipeline.execute_pipeline(ctx)

    def replicate_all(self) -> ReplicationSession:
        """Synchronous wrapper for replicate_all_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        return loop.run_until_complete(self.replicate_all_async())

    def get_supported_capabilities(self) -> List[str]:
        """Return list of all 25 capabilities supported across domain replicators."""
        return self.registry.list_all_capabilities()

    def get_health(self) -> Dict[str, Any]:
        """Return operational health report for Platform 3."""
        return {
            "status": "HEALTHY",
            "capabilities_count": len(self.get_supported_capabilities()),
            "domain_count": len(self.registry.list_domains()),
            "leader_id": self.distributed_coordinator.get_leader(),
        }
