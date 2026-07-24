"""
EnterpriseResiliencePlatformV5 — Canonical Public Facade for Platform 5.

This is the ONLY public entry point. Zero business logic.
All execution delegated to the pipeline orchestrator and domain modules.
"""

import asyncio
import time
import uuid
from typing import Optional, Dict, Any, List

from akaal.resilience_eng.core.config import ResilienceEngConfig, ResilienceEngProfile
from akaal.resilience_eng.core.context import ResilienceEngContext
from akaal.resilience_eng.core.session import ResilienceEngSession

# Domain Modules
from akaal.resilience_eng.domain.chaos_domain import ChaosDomain
from akaal.resilience_eng.domain.experiment_domain import ExperimentDomain
from akaal.resilience_eng.domain.safety_domain import SafetyDomain
from akaal.resilience_eng.domain.learning_domain import LearningDomain
from akaal.resilience_eng.domain.recovery_validation_domain import RecoveryValidationDomain
from akaal.resilience_eng.domain.governance_domain import GovernanceDomain

# Subsystems
from akaal.resilience_eng.provenance.provenance_manager import ExperimentProvenanceManager
from akaal.resilience_eng.digital_twin.fidelity import DigitalTwinEngine
from akaal.resilience_eng.dependencies.graph import ExperimentDependencyGraph
from akaal.resilience_eng.certification.recovery_certifier import RecoveryCertificationEngine
from akaal.resilience_eng.taxonomy.classifier import FailureTaxonomyClassifier
from akaal.resilience_eng.security.authorization import SecurityAuthorizationEngine
from akaal.resilience_eng.isolation.experiment_context import ExperimentIsolationContext
from akaal.resilience_eng.approval.workflow import ApprovalWorkflowEngine
from akaal.resilience_eng.versioning.version_manager import ExperimentVersionManager
from akaal.resilience_eng.resources.reservation_engine import ResourceReservationEngine
from akaal.resilience_eng.confidence.engine import ConfidenceEngine
from akaal.resilience_eng.cost.estimator import ExperimentCostEstimator
from akaal.resilience_eng.policy.engine import ResiliencePolicyEngine
from akaal.resilience_eng.replay.replay_engine import ExperimentReplayEngine
from akaal.resilience_eng.maturity.assessment import ResilienceMaturityEngine
from akaal.resilience_eng.scenario.orchestrator import ScenarioOrchestrationEngine
from akaal.resilience_eng.library.catalog import ResilienceExperimentLibrary
from akaal.resilience_eng.safety.blast_radius import BlastRadiusController, SafetyGuardrailsEngine
from akaal.resilience_eng.scoring.score_engine import ResilienceScoreEngine
from akaal.resilience_eng.validation.recovery_validator import AutomaticRecoveryValidator
from akaal.resilience_eng.learning.learning_engine import ContinuousResilienceLearningEngine
from akaal.resilience_eng.reporting.report_generator import EnterpriseResilienceReportGenerator
from akaal.resilience_eng.services.audit import ResilienceAuditTrailService, ResilienceHealthService, ResilienceObservabilityService
from akaal.resilience_eng.cache.resilience_cache import ResilienceCache
from akaal.resilience_eng.events.event_bus import ResilienceEventBus
from akaal.resilience_eng.distributed.coordinator import DistributedExperimentCoordinator
from akaal.resilience_eng.pipeline.orchestrator import ResiliencePipelineOrchestrator
from akaal.resilience_eng.analytics.analytics_engine import AnalyticsEngine


class EnterpriseResiliencePlatformV5:
    """
    Enterprise Resilience Validation Platform V5.

    Public facade for Phase 11 Platform 5.
    Responsible for enterprise resilience validation, certification, experiment governance,
    and continuous resilience improvement across the AKAAL platform.

    Consumes Platform 1, 2, 3, and 4 exclusively via their public API facades.
    """

    def __init__(
        self,
        config: Optional[ResilienceEngConfig] = None,
        profile: ResilienceEngProfile = ResilienceEngProfile.ENTERPRISE,
    ):
        self._config = config or ResilienceEngConfig()
        self._profile = profile

        # Build subsystems
        self._event_bus = ResilienceEventBus()
        self._cache = ResilienceCache()
        self._audit_service = ResilienceAuditTrailService()
        self._health_service = ResilienceHealthService()
        self._observability_service = ResilienceObservabilityService()
        self._provenance_mgr = ExperimentProvenanceManager()
        self._twin_engine = DigitalTwinEngine()
        self._dep_graph = ExperimentDependencyGraph()
        self._certification_engine = RecoveryCertificationEngine()
        self._taxonomy_classifier = FailureTaxonomyClassifier()
        self._security_engine = SecurityAuthorizationEngine()
        self._approval_engine = ApprovalWorkflowEngine()
        self._version_mgr = ExperimentVersionManager()
        self._reservation_engine = ResourceReservationEngine()
        self._confidence_engine = ConfidenceEngine()
        self._cost_estimator = ExperimentCostEstimator()
        self._policy_engine = ResiliencePolicyEngine()
        self._replay_engine = ExperimentReplayEngine()
        self._maturity_engine = ResilienceMaturityEngine()
        self._scenario_orchestrator = ScenarioOrchestrationEngine()
        self._experiment_library = ResilienceExperimentLibrary()
        self._blast_radius_controller = BlastRadiusController()
        self._safety_guardrails = SafetyGuardrailsEngine()
        self._score_engine = ResilienceScoreEngine()
        self._recovery_validator = AutomaticRecoveryValidator()
        self._learning_engine = ContinuousResilienceLearningEngine()
        self._report_generator = EnterpriseResilienceReportGenerator()
        self._distributed_coordinator = DistributedExperimentCoordinator()
        self._analytics_engine = AnalyticsEngine()

        # Pipeline orchestrator
        self._pipeline = ResiliencePipelineOrchestrator()

        # Domain modules (6)
        self._domain_modules = [
            ChaosDomain(),
            ExperimentDomain(),
            SafetyDomain(),
            LearningDomain(),
            RecoveryValidationDomain(),
            GovernanceDomain(),
        ]

        self._initialized_at = time.time()

    def _build_context(self) -> ResilienceEngContext:
        return ResilienceEngContext(
            config=self._config,
            profile=self._profile,
            provenance_manager=self._provenance_mgr,
            digital_twin_engine=self._twin_engine,
            dependency_graph=self._dep_graph,
            certification_engine=self._certification_engine,
            taxonomy_classifier=self._taxonomy_classifier,
            security_engine=self._security_engine,
            approval_engine=self._approval_engine,
            version_manager=self._version_mgr,
            reservation_engine=self._reservation_engine,
            confidence_engine=self._confidence_engine,
            cost_estimator=self._cost_estimator,
            policy_engine=self._policy_engine,
            replay_engine=self._replay_engine,
            maturity_engine=self._maturity_engine,
            scenario_orchestrator=self._scenario_orchestrator,
            experiment_library=self._experiment_library,
            blast_radius_controller=self._blast_radius_controller,
            safety_guardrails=self._safety_guardrails,
            score_engine=self._score_engine,
            recovery_validator=self._recovery_validator,
            learning_engine=self._learning_engine,
            report_generator=self._report_generator,
            audit_service=self._audit_service,
            observability_service=self._observability_service,
            cache=self._cache,
            event_bus=self._event_bus,
            distributed_coordinator=self._distributed_coordinator,
        )

    async def run_resilience_validation_async(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a complete resilience validation pipeline run asynchronously."""
        exp_id = experiment_id or str(uuid.uuid4())
        context = self._build_context()

        session = await self._pipeline.execute_pipeline(context, self._domain_modules, exp_id)

        # Post-pipeline: generate reports, learning insights, observability
        all_results = session.results
        report_suite = self._report_generator.generate_full_report_suite(exp_id, all_results)
        learning_insights = self._learning_engine.generate_learning_insights(all_results)
        maturity = self._maturity_engine.evaluate_maturity()
        observability = self._observability_service.get_observability_metrics()
        health = self._health_service.get_platform_health()

        return {
            "experiment_id": exp_id,
            "session_id": session.session_id,
            "session_status": session.state.value,
            "total_actions_executed": session.total_actions_executed,
            "domain_results_count": len(all_results),
            "is_successful": session.is_successful,
            "events_published": self._event_bus.published_count(),
            "report_suite": report_suite,
            "learning_insights": learning_insights,
            "maturity_level": maturity.overall_maturity_level,
            "observability": observability,
            "platform_health": health,
        }

    def run_resilience_validation(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous wrapper for run_resilience_validation_async."""
        return asyncio.run(self.run_resilience_validation_async(experiment_id))

    def get_platform_health(self) -> Dict[str, Any]:
        return self._health_service.get_platform_health()

    def get_observability_metrics(self) -> Dict[str, Any]:
        return self._observability_service.get_observability_metrics()

    def get_experiment_library(self) -> List[str]:
        return self._experiment_library.list_templates()

    def get_maturity_assessment(self) -> Dict[str, Any]:
        m = self._maturity_engine.evaluate_maturity()
        return {
            "reliability_score": m.reliability_score,
            "recovery_score": m.recovery_score,
            "validation_score": m.validation_score,
            "overall_maturity_level": m.overall_maturity_level,
            "recommendations": m.recommendations,
        }

    @property
    def platform_name(self) -> str:
        return "EnterpriseResiliencePlatformV5"

    @property
    def version(self) -> str:
        return "5.0.0"

    @property
    def profile(self) -> str:
        return self._profile.value
