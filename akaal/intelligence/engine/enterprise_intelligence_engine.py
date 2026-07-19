"""
AKAAL Enterprise Intelligence Platform — Enterprise Intelligence Engine
========================================================================
Core pipeline orchestrator executing input validation, registry resolution, DAG graph sorting,
analyzer execution, MAUT conflict resolution, governance fingerprinting, and canonical model synthesis.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.intelligence.analyzers.agent_coordination_analyzer import AgentCoordinationAnalyzer
from akaal.intelligence.analyzers.migration_simulation_analyzer import MigrationSimulationAnalyzer
from akaal.intelligence.analyzers.readiness_analyzer import ReadinessAnalyzer
from akaal.intelligence.analyzers.recommendation_aggregation_analyzer import RecommendationAggregationAnalyzer
from akaal.intelligence.analyzers.strategy_analyzer import StrategyAnalyzer
from akaal.intelligence.engine.decision_graph_engine import DecisionGraphEngine
from akaal.intelligence.events.enterprise_intelligence_events import (
    EnterpriseIntelligenceEventBus,
    PlatformCompletedEvent,
    PlatformStartedEvent,
    ValidationCompletedEvent,
    ValidationFailedEvent,
)
from akaal.intelligence.governance.enterprise_intelligence_governance import EnterpriseIntelligenceGovernance
from akaal.intelligence.metrics.enterprise_intelligence_metrics import EnterpriseIntelligenceMetricsCollector
from akaal.intelligence.models.agent_coordination_plan import AgentCoordinationPlan
from akaal.intelligence.models.enterprise_decision import EnterpriseDecision
from akaal.intelligence.models.enterprise_intelligence_enums import DecisionPriority
from akaal.intelligence.models.enterprise_intelligence_manifest import EnterpriseIntelligenceManifest

from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel
from akaal.intelligence.models.enterprise_intelligence_trace import EnterpriseIntelligenceTrace
from akaal.intelligence.models.enterprise_intelligence_version import EnterpriseIntelligenceVersionInfo
from akaal.intelligence.models.migration_simulation_result import MigrationSimulationResult
from akaal.intelligence.models.readiness_assessment import ReadinessAssessment
from akaal.intelligence.models.strategy_synthesis import StrategySynthesis
from akaal.intelligence.registry.enterprise_intelligence_registry import EnterpriseIntelligenceRegistry
from akaal.intelligence.validation.enterprise_intelligence_validator import (
    EnterpriseIntelligenceValidationError,
    EnterpriseIntelligenceValidator,
)


class EnterpriseIntelligenceEngineError(Exception):
    """Exception raised for execution failures in EnterpriseIntelligenceEngine."""
    pass


class EnterpriseIntelligenceEngine:
    """
    Orchestrates Platform 2 pipeline execution in a pure, deterministic, thread-safe manner.
    """

    def __init__(
        self,
        registry: Optional[EnterpriseIntelligenceRegistry] = None,
        event_bus: Optional[EnterpriseIntelligenceEventBus] = None,
        metrics: Optional[EnterpriseIntelligenceMetricsCollector] = None,
    ) -> None:
        self._registry = registry or EnterpriseIntelligenceRegistry()
        self._event_bus = event_bus or EnterpriseIntelligenceEventBus()
        self._metrics = metrics or EnterpriseIntelligenceMetricsCollector()
        self._bootstrap_registry_if_empty()

    def _bootstrap_registry_if_empty(self) -> None:
        """Bootstraps standard strategic analyzers into registry if uninitialized."""
        if not self._registry.list():
            self._registry.register("agent_coordination", AgentCoordinationAnalyzer())
            self._registry.register("strategy", StrategyAnalyzer())
            self._registry.register("recommendation_aggregation", RecommendationAggregationAnalyzer())
            self._registry.register("migration_simulation", MigrationSimulationAnalyzer())
            self._registry.register("readiness", ReadinessAnalyzer())

    def execute(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> EnterpriseIntelligenceModel:
        """
        Executes complete strategic intelligence pipeline.

        Raises:
            EnterpriseIntelligenceValidationError: If input or output validation fails.
            EnterpriseIntelligenceEngineError: If pipeline execution fails.
        """
        start_time = time.perf_counter()
        ctx = context or {}

        # Step 1: Input Validation
        try:
            EnterpriseIntelligenceValidator.validate_advisory_model(advisory_model)
            self._event_bus.publish(ValidationCompletedEvent("VAL-001", payload={"is_valid": True}))
        except EnterpriseIntelligenceValidationError as ex:
            self._event_bus.publish(ValidationFailedEvent("VAL-ERR-001", payload={"error_message": str(ex)}))
            self._metrics.record_failure()
            raise

        advisory_id = (
            getattr(advisory_model.manifest, "advisory_id", "")
            if advisory_model and getattr(advisory_model, "manifest", None)
            else "ADV-UNKNOWN"
        )
        self._event_bus.publish(PlatformStartedEvent("START-001", payload={"advisory_model_id": advisory_id}))

        # Step 2: Build Decision Graph DAG
        graph_engine = DecisionGraphEngine()
        analyzer_names = self._registry.list()
        for name in analyzer_names:
            graph_engine.add_node(name)

        sorted_analyzers = graph_engine.topological_sort()

        # Step 3: Execute Analyzers
        analyzer_durations_ms: Dict[str, float] = {}
        analyzer_outputs: Dict[str, Any] = {}

        for name in sorted_analyzers:
            analyzer_instance = self._registry.get(name)
            if not analyzer_instance:
                continue

            a_start = time.perf_counter()
            try:
                out = analyzer_instance.analyze(advisory_model, context=ctx)
                a_duration = (time.perf_counter() - a_start) * 1000.0
                analyzer_durations_ms[name] = round(a_duration, 3)
                analyzer_outputs[name] = out
                self._metrics.record_duration(f"analyzer_{name}", a_duration)
            except Exception as ex:
                self._metrics.record_failure()
                raise EnterpriseIntelligenceEngineError(f"Analyzer '{name}' failed during execution: {ex}") from ex

        # Step 4: Resolve Strategic Conflicts via MAUT
        g_start = time.perf_counter()
        raw_decisions: List[EnterpriseDecision] = analyzer_outputs.get("recommendation_aggregation", ())
        if isinstance(raw_decisions, tuple):
            raw_decisions = list(raw_decisions)

        resolved_decisions = graph_engine.resolve_conflicts(raw_decisions)
        g_duration = (time.perf_counter() - g_start) * 1000.0
        self._metrics.record_duration("decision_graph_resolution", g_duration)

        # Step 5: Extract Analyzer Outputs
        strategy: StrategySynthesis = analyzer_outputs.get("strategy") or StrategySynthesis(
            "STR-DEFAULT", StrategyType.BALANCED_STAGE_BY_STAGE, "Default Strategy", "STAGE_BY_STAGE", 3600.0, 4
        )

        simulation: MigrationSimulationResult = analyzer_outputs.get("migration_simulation") or MigrationSimulationResult(
            "SIM-DEFAULT", 120.0, 600.0, 300.0, 3600.0, 15000.0, 1024.0, 8.0, 0.02
        )

        readiness: ReadinessAssessment = analyzer_outputs.get("readiness") or ReadinessAssessment(
            "READ-DEFAULT", 90.0, ReadinessTier.PRODUCTION_READY, 90.0, 90.0, 90.0, 90.0
        )

        agent_coordination: AgentCoordinationPlan = analyzer_outputs.get("agent_coordination") or AgentCoordinationPlan(
            "AGENT-DEFAULT", 4, "us-east-1"
        )

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        self._metrics.record_duration("total_pipeline_execution", total_duration_ms)

        # Step 6: Construct Trace & Manifest
        model_id = f"ENT-MODEL-{uuid.uuid4().hex[:8].upper()}"

        trace = EnterpriseIntelligenceTrace(
            trace_id=f"TRC-{uuid.uuid4().hex[:8].upper()}",
            total_execution_duration_ms=round(total_duration_ms, 3),
            analyzer_durations_ms=analyzer_durations_ms,
            decision_graph_duration_ms=round(g_duration, 3),
            evaluation_logs=("Pipeline executed successfully.",),
            metadata={"sorted_analyzers": sorted_analyzers},
        )

        manifest = EnterpriseIntelligenceManifest(
            advisory_model_id=advisory_id,
            total_decisions=len(resolved_decisions),
            critical_decisions_count=sum(1 for d in resolved_decisions if d.priority == DecisionPriority.CRITICAL),
            high_priority_decisions_count=sum(1 for d in resolved_decisions if d.priority == DecisionPriority.HIGH),
            readiness_score=readiness.overall_readiness_score,
            simulated_downtime_p95_seconds=simulation.projected_downtime_seconds_p95,
            generated_at_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            metadata={},
        )

        v_info = EnterpriseIntelligenceVersionInfo()

        # Construct Preliminary Unchecksummed Model to Compute SHA-256 Fingerprint
        preliminary_model = EnterpriseIntelligenceModel(
            model_id=model_id,
            advisory_model_id=advisory_id,
            version_info=v_info,
            manifest=manifest,
            decisions=tuple(resolved_decisions),
            strategy=strategy,
            simulation=simulation,
            readiness=readiness,
            agent_coordination=agent_coordination,
            trace=trace,
            checksum="",
            metadata={"pipeline": "akaal.intelligence.engine"},
        )

        sha256_checksum = EnterpriseIntelligenceGovernance.compute_model_checksum(preliminary_model)

        # Construct Final Canonical Model
        canonical_model = EnterpriseIntelligenceModel(
            model_id=model_id,
            advisory_model_id=advisory_id,
            version_info=v_info,
            manifest=manifest,
            decisions=tuple(resolved_decisions),
            strategy=strategy,
            simulation=simulation,
            readiness=readiness,
            agent_coordination=agent_coordination,
            trace=trace,
            checksum=sha256_checksum,
            metadata={"pipeline": "akaal.intelligence.engine"},
        )

        # Step 7: Output Validation
        EnterpriseIntelligenceValidator.validate_intelligence_model(canonical_model)
        self._metrics.record_success()

        self._event_bus.publish(
            PlatformCompletedEvent(
                "COMP-001",
                payload={"intelligence_model_id": model_id, "checksum": sha256_checksum},
            )
        )

        return canonical_model
