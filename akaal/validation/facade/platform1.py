"""EnterpriseValidationPlatformV1: Primary Canonical Facade for Phase 11 Platform 1."""

import asyncio
from typing import Any, Dict, List, Optional
from akaal.validation.core.context import ValidationContext
from akaal.validation.core.config import ValidationConfig, ValidationProfile, PolicyProfile
from akaal.validation.core.session import ValidationSession
from akaal.validation.core.registry import ValidatorRegistry
from akaal.validation.services.merkle import MerkleService
from akaal.validation.services.evidence import EvidenceService
from akaal.validation.services.replay import ReplayService
from akaal.validation.services.explainability import ExplainabilityService
from akaal.validation.services.observability import ObservabilityService
from akaal.validation.cache.validation_cache import ValidationCache
from akaal.validation.events.event_bus import EventBus
from akaal.validation.events.publishers import EventPublisher
from akaal.validation.policy.engine import PolicyEngine
from akaal.validation.plugins.registry import PluginRegistry
from akaal.validation.plugins.loader import PluginLoader
from akaal.validation.distributed.coordinator import DistributedCoordinator
from akaal.validation.pipeline.orchestrator import ValidationPipeline

# 8 Domain-Driven Validators
from akaal.validation.domain.structural import StructuralValidator
from akaal.validation.domain.data import DataValidator
from akaal.validation.domain.integrity import IntegrityValidator
from akaal.validation.domain.statistical import StatisticalValidator
from akaal.validation.domain.semantic import SemanticValidator
from akaal.validation.domain.performance import PerformanceValidator
from akaal.validation.domain.enterprise import EnterpriseValidator
from akaal.validation.domain.scoring import ScoringValidator


class EnterpriseValidationPlatformV1:
    """Canonical Enterprise Entry Point for all 33 Validation Capabilities."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

        # Initialize Infrastructure Services
        self.merkle_service = MerkleService()
        self.evidence_service = EvidenceService()
        self.replay_service = ReplayService()
        self.explainability_service = ExplainabilityService()
        self.observability_service = ObservabilityService()

        # Initialize Cache and EventBus
        self.cache = ValidationCache(default_ttl_seconds=self.config.cache_ttl_seconds)
        self.event_bus = EventBus()
        self.publisher = EventPublisher(self.event_bus)

        # Initialize Policy Engine
        self.policy_engine = PolicyEngine(profile=self.config.policy_profile)

        # Initialize Plugins & Registry
        self.plugin_registry = PluginRegistry()
        self.plugin_loader = PluginLoader(self.plugin_registry)

        # Initialize Distributed Coordinator
        self.distributed_coordinator = DistributedCoordinator(num_workers=self.config.max_parallel_workers)

        # Initialize Registry & Register 8 Domain Validators
        self.registry = ValidatorRegistry()
        self._register_default_domain_validators()

        # Initialize Pure Pipeline Orchestrator
        self.pipeline = ValidationPipeline(registry=self.registry)

    def _register_default_domain_validators(self) -> None:
        """Register the 8 domain-driven validators covering all 33 capabilities."""
        self.registry.register_domain_validator(StructuralValidator())
        self.registry.register_domain_validator(DataValidator())
        self.registry.register_domain_validator(IntegrityValidator())
        self.registry.register_domain_validator(StatisticalValidator())
        self.registry.register_domain_validator(SemanticValidator())
        self.registry.register_domain_validator(PerformanceValidator())
        self.registry.register_domain_validator(EnterpriseValidator())
        self.registry.register_domain_validator(ScoringValidator())

    def create_context(
        self, source_adapter: Any = None, target_adapter: Any = None, **kwargs
    ) -> ValidationContext:
        """Construct a ValidationContext injected with all platform services."""
        return ValidationContext(
            source_adapter=source_adapter,
            target_adapter=target_adapter,
            config=self.config,
            validation_profile=self.config.profile,
            policy_engine=self.policy_engine,
            evidence_service=self.evidence_service,
            merkle_service=self.merkle_service,
            replay_service=self.replay_service,
            explainability_service=self.explainability_service,
            observability_service=self.observability_service,
            cache=self.cache,
            event_bus=self.event_bus,
            distributed_coordinator=self.distributed_coordinator,
            runtime_metadata={"validator_registry": self.registry, **kwargs},
        )

    async def validate_all_async(
        self, source_adapter: Any = None, target_adapter: Any = None
    ) -> ValidationSession:
        """Execute all 33 capabilities across all 8 domain validators asynchronously."""
        ctx = self.create_context(source_adapter, target_adapter)
        return await self.pipeline.execute_pipeline(ctx)

    def validate_all(
        self, source_adapter: Any = None, target_adapter: Any = None
    ) -> ValidationSession:
        """Synchronous wrapper for validate_all_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        return loop.run_until_complete(self.validate_all_async(source_adapter, target_adapter))

    def get_supported_capabilities(self) -> List[str]:
        """Return list of all 33 capabilities supported across domain validators."""
        return self.registry.list_all_capabilities()
