"""EnterpriseSelfHealingPlatformV2: Canonical Facade for Phase 11 Platform 2."""

import asyncio
from typing import Any, Dict, List, Optional
from akaal.healing.core.context import HealingContext
from akaal.healing.core.config import HealingConfig, HealingProfile, ApprovalMode
from akaal.healing.core.session import HealingSession
from akaal.healing.core.registry import HealerRegistry

# Platform 1 Integration
from akaal.validation import EnterpriseValidationPlatformV1

# Subsystem Engines
from akaal.healing.decision.engine import DecisionEngine
from akaal.healing.dependency.graph import RepairDependencyGraph
from akaal.healing.sandbox.sandbox import RepairSandbox
from akaal.healing.scheduler.scheduler import RepairScheduler
from akaal.healing.recovery.multi_source import MultiSourceRecovery
from akaal.healing.conflicts.locks import RepairLockManager
from akaal.healing.business.analyzer import BusinessImpactAnalyzer

# Services, Cache, Events, Policy, Plugins, Distributed
from akaal.healing.services.root_cause import RootCauseAnalysisService
from akaal.healing.services.verification import RepairVerificationService
from akaal.healing.services.scoring import ConfidenceScoringService
from akaal.healing.services.rollback import RollbackService
from akaal.healing.services.pattern_learning import PatternLearningService
from akaal.healing.services.recommendation import RecommendationEngineService
from akaal.healing.services.audit import RepairAuditTrailService
from akaal.healing.services.observability import ObservabilityService
from akaal.healing.cache.healing_cache import HealingCache
from akaal.healing.events.event_bus import HealingEventBus
from akaal.healing.events.publishers import HealingEventPublisher
from akaal.healing.policy.engine import HealingPolicyEngine
from akaal.healing.plugins.registry import PluginRegistry
from akaal.healing.distributed.coordinator import DistributedHealingCoordinator
from akaal.healing.pipeline.orchestrator import HealingPipeline

# 6 Domain Healers
from akaal.healing.domain.core_repair import CoreRepairHealer
from akaal.healing.domain.intelligent import IntelligentHealer
from akaal.healing.domain.safe_execution import SafeExecutionHealer
from akaal.healing.domain.recovery import EnterpriseRecoveryHealer
from akaal.healing.domain.governance import GovernanceHealer
from akaal.healing.domain.learning import LearningHealer


class EnterpriseSelfHealingPlatformV2:
    """Canonical Enterprise Entry Point for all 25 Self-Healing Capabilities."""

    def __init__(self, config: Optional[HealingConfig] = None, validation_platform: Optional[EnterpriseValidationPlatformV1] = None):
        self.config = config or HealingConfig()

        # Platform 1 Facade Integration
        self.validation_platform = validation_platform or EnterpriseValidationPlatformV1()

        # Initialize Subsystem Engines
        self.decision_engine = DecisionEngine()
        self.dependency_graph = RepairDependencyGraph()
        self.sandbox_engine = RepairSandbox()
        self.repair_scheduler = RepairScheduler()
        self.multi_source_recovery = MultiSourceRecovery()
        self.lock_manager = RepairLockManager()
        self.business_analyzer = BusinessImpactAnalyzer()

        # Initialize Infrastructure Services
        self.root_cause_service = RootCauseAnalysisService()
        self.verification_service = RepairVerificationService()
        self.scoring_service = ConfidenceScoringService()
        self.rollback_service = RollbackService()
        self.pattern_learning_service = PatternLearningService()
        self.recommendation_service = RecommendationEngineService()
        self.audit_service = RepairAuditTrailService()
        self.observability_service = ObservabilityService()

        # Initialize Cache and EventBus
        self.cache = HealingCache()
        self.event_bus = HealingEventBus()
        self.publisher = HealingEventPublisher(self.event_bus)

        # Initialize Policy Engine & Plugin Registry
        self.policy_engine = HealingPolicyEngine(profile=self.config.profile, approval_mode=self.config.approval_mode)
        self.plugin_registry = PluginRegistry()

        # Initialize Distributed Coordinator
        self.distributed_coordinator = DistributedHealingCoordinator(num_workers=self.config.max_parallel_workers)

        # Initialize Healer Registry & Register 6 Domain Healers
        self.registry = HealerRegistry()
        self._register_default_domain_healers()

        # Initialize Pure Pipeline Orchestrator
        self.pipeline = HealingPipeline(registry=self.registry)

    def _register_default_domain_healers(self) -> None:
        """Register 6 Domain-Driven Healers covering all 25 capabilities."""
        self.registry.register_domain_healer(CoreRepairHealer())
        self.registry.register_domain_healer(IntelligentHealer())
        self.registry.register_domain_healer(SafeExecutionHealer())
        self.registry.register_domain_healer(EnterpriseRecoveryHealer())
        self.registry.register_domain_healer(GovernanceHealer())
        self.registry.register_domain_healer(LearningHealer())

    def create_context(
        self, source_adapter: Any = None, target_adapter: Any = None, **kwargs
    ) -> HealingContext:
        """Construct a HealingContext injected with Platform 1 & Platform 2 services."""
        val_ctx = self.validation_platform.create_context(source_adapter, target_adapter)
        return HealingContext(
            validation_context=val_ctx,
            validation_platform=self.validation_platform,
            source_adapter=source_adapter,
            target_adapter=target_adapter,
            config=self.config,
            profile=self.config.profile,
            decision_engine=self.decision_engine,
            dependency_graph=self.dependency_graph,
            sandbox_engine=self.sandbox_engine,
            repair_scheduler=self.repair_scheduler,
            multi_source_recovery=self.multi_source_recovery,
            business_analyzer=self.business_analyzer,
            policy_engine=self.policy_engine,
            root_cause_service=self.root_cause_service,
            verification_service=self.verification_service,
            scoring_service=self.scoring_service,
            rollback_service=self.rollback_service,
            pattern_learning_service=self.pattern_learning_service,
            recommendation_service=self.recommendation_service,
            audit_service=self.audit_service,
            observability_service=self.observability_service,
            cache=self.cache,
            event_bus=self.event_bus,
            distributed_coordinator=self.distributed_coordinator,
            runtime_metadata={"healer_registry": self.registry, **kwargs},
        )

    async def heal_all_async(
        self, source_adapter: Any = None, target_adapter: Any = None
    ) -> HealingSession:
        """Execute self-healing pipeline across all 6 domain healers asynchronously."""
        ctx = self.create_context(source_adapter, target_adapter)
        return await self.pipeline.execute_pipeline(ctx)

    def heal_all(
        self, source_adapter: Any = None, target_adapter: Any = None
    ) -> HealingSession:
        """Synchronous wrapper for heal_all_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        return loop.run_until_complete(self.heal_all_async(source_adapter, target_adapter))

    def get_supported_capabilities(self) -> List[str]:
        """Return list of all 25 capabilities supported across domain healers."""
        return self.registry.list_all_capabilities()
