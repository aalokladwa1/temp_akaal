"""EnterpriseReliabilityPlatformV4: Canonical Public Facade Entry Point for Platform 4."""

import asyncio
from typing import Optional, Dict, Any, List

from akaal.reliability.core.config import ReliabilityConfig, ReliabilityProfile
from akaal.reliability.core.context import ReliabilityContext
from akaal.reliability.core.session import ReliabilitySession
from akaal.reliability.core.registry import ReliabilityRegistry
from akaal.reliability.decision.engine import ReliabilityDecisionEngine
from akaal.reliability.state.machine import ReliabilityStateMachine
from akaal.reliability.knowledge.knowledge_base import ReliabilityKnowledgeBase
from akaal.reliability.diagnostics.root_cause import RootCauseAnalysisEngine, DependencyHealthGraph, SelfDiagnosticsEngine, FailurePredictor, FailurePatternLearningEngine
from akaal.reliability.scheduler.recovery_scheduler import ReliabilityRetryScheduler, ReliabilityRecoveryScheduler, MaintenanceWindowScheduler
from akaal.reliability.recovery.orchestrator import StatefulRecoveryOrchestrator
from akaal.reliability.resilience.circuit_breaker import CircuitBreakerManager, BulkheadIsolationManager, AdaptiveBackpressureController, AdaptiveLoadShedder, IntelligentRetryEngine
from akaal.reliability.dashboard.reliability_summary import ReliabilitySummary
from akaal.reliability.timeline.incident_timeline import IncidentTimelineEngine
from akaal.reliability.analytics.analytics_engine import AnalyticsEngine
from akaal.reliability.domain.reliability_domain import ReliabilityDomain
from akaal.reliability.domain.recovery_domain import RecoveryDomain
from akaal.reliability.domain.diagnostics_domain import DiagnosticsDomain
from akaal.reliability.domain.resilience_domain import ResilienceDomain
from akaal.reliability.domain.governance_domain import GovernanceDomain
from akaal.reliability.domain.observability_domain import ObservabilityDomain
from akaal.reliability.services.audit import ReliabilityAuditTrailService, ReliabilityObservabilityService, HealthScoringEngine
from akaal.reliability.policy.engine import ReliabilityPolicyEngine
from akaal.reliability.events.event_bus import ReliabilityEventBus
from akaal.reliability.cache.reliability_cache import ReliabilityCache
from akaal.reliability.distributed.coordinator import DistributedReliabilityCoordinator
from akaal.reliability.pipeline.orchestrator import ReliabilityPipeline


class EnterpriseReliabilityPlatformV4:
    """Canonical Public Facade Entry Point for Phase 11 Platform 4 Enterprise Reliability Platform."""

    def __init__(self, config: Optional[ReliabilityConfig] = None):
        self.config = config or ReliabilityConfig()

        # Instantiate Infrastructure Subsystems
        self.decision_engine = ReliabilityDecisionEngine()
        self.state_machine = ReliabilityStateMachine()
        self.knowledge_base = ReliabilityKnowledgeBase()

        self.dep_graph = DependencyHealthGraph()
        self.root_cause_engine = RootCauseAnalysisEngine(self.dep_graph)
        self.self_diagnostics = SelfDiagnosticsEngine()
        self.failure_predictor = FailurePredictor()
        self.pattern_learning = FailurePatternLearningEngine()

        self.retry_scheduler = ReliabilityRetryScheduler()
        self.recovery_scheduler = ReliabilityRecoveryScheduler()
        self.maintenance_scheduler = MaintenanceWindowScheduler()

        self.recovery_orchestrator = StatefulRecoveryOrchestrator()
        self.circuit_breaker_mgr = CircuitBreakerManager()
        self.bulkhead_mgr = BulkheadIsolationManager()
        self.backpressure_controller = AdaptiveBackpressureController()
        self.load_shedder = AdaptiveLoadShedder()
        self.retry_engine = IntelligentRetryEngine()

        self.incident_timeline = IncidentTimelineEngine()
        self.analytics_engine = AnalyticsEngine()
        self.policy_engine = ReliabilityPolicyEngine(self.config.profile)
        self.audit_service = ReliabilityAuditTrailService()
        self.observability_service = ReliabilityObservabilityService()
        self.health_scoring = HealthScoringEngine()
        self.cache = ReliabilityCache()
        self.event_bus = ReliabilityEventBus()
        self.distributed_coordinator = DistributedReliabilityCoordinator()

        # Register 6 Domain Modules
        self.registry = ReliabilityRegistry()
        self.registry.register_domain_module(ReliabilityDomain())
        self.registry.register_domain_module(RecoveryDomain())
        self.registry.register_domain_module(DiagnosticsDomain())
        self.registry.register_domain_module(ResilienceDomain())
        self.registry.register_domain_module(GovernanceDomain())
        self.registry.register_domain_module(ObservabilityDomain())

        # Instantiate Pipeline
        self.pipeline = ReliabilityPipeline(self.registry)

    def create_context(self) -> ReliabilityContext:
        """Create dependency-injected execution context."""
        return ReliabilityContext(
            config=self.config,
            profile=self.config.profile,
            decision_engine=self.decision_engine,
            state_machine=self.state_machine,
            knowledge_base=self.knowledge_base,
            diagnostics_engine=self.root_cause_engine,
            scheduler=self.recovery_scheduler,
            recovery_orchestrator=self.recovery_orchestrator,
            resilience_manager=self.circuit_breaker_mgr,
            dashboard_models=ReliabilitySummary(),
            incident_timeline=self.incident_timeline,
            analytics_engine=self.analytics_engine,
            policy_engine=self.policy_engine,
            audit_service=self.audit_service,
            observability_service=self.observability_service,
            cache=self.cache,
            event_bus=self.event_bus,
            distributed_coordinator=self.distributed_coordinator,
        )

    def run_reliability_suite(self) -> ReliabilitySession:
        """Synchronous entry point executing complete reliability pipeline."""
        return asyncio.run(self.run_reliability_suite_async())

    async def run_reliability_suite_async(self) -> ReliabilitySession:
        """Asynchronous entry point executing complete reliability pipeline."""
        context = self.create_context()
        session = ReliabilitySession()
        return await self.pipeline.execute_pipeline(context, session)

    def get_dashboard_summary(self) -> ReliabilitySummary:
        """Get canonical reliability summary dashboard object."""
        return ReliabilitySummary(active_profile=self.config.profile.value)
