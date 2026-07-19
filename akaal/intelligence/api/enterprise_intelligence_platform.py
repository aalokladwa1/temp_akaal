"""
AKAAL Enterprise Intelligence Platform — Public Facade API
===========================================================
The single public entry point into Platform 2 (Enterprise Intelligence Subsystem).
Hides internal registry, analyzers, and decision graph orchestration details.
"""

from typing import Any, Dict, List, Optional
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.intelligence.engine.enterprise_intelligence_engine import EnterpriseIntelligenceEngine
from akaal.intelligence.events.enterprise_intelligence_events import EnterpriseIntelligenceEventBus
from akaal.intelligence.metrics.enterprise_intelligence_metrics import EnterpriseIntelligenceMetricsCollector
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel
from akaal.intelligence.registry.enterprise_intelligence_registry import EnterpriseIntelligenceRegistry
from akaal.intelligence.serialization.enterprise_intelligence_serializer import EnterpriseIntelligenceSerializer
from akaal.intelligence.validation.enterprise_intelligence_validator import EnterpriseIntelligenceValidator


class EnterpriseIntelligencePlatform:
    """
    Public Facade API for Platform 2 Enterprise Intelligence Subsystem.
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
        self._engine = EnterpriseIntelligenceEngine(
            registry=self._registry,
            event_bus=self._event_bus,
            metrics=self._metrics,
        )

    def analyze(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> EnterpriseIntelligenceModel:
        """
        Executes complete strategic intelligence pipeline on an immutable MigrationAdvisoryModel.
        """
        return self._engine.execute(advisory_model, context=context)

    def execute(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> EnterpriseIntelligenceModel:
        """
        Alias for analyze().
        """
        return self.analyze(advisory_model, context=context)

    @staticmethod
    def validate(model: EnterpriseIntelligenceModel) -> bool:
        """
        Validates an EnterpriseIntelligenceModel schema and decision uniqueness.
        """
        return EnterpriseIntelligenceValidator.validate_intelligence_model(model)

    @staticmethod
    def to_dict(model: EnterpriseIntelligenceModel) -> Dict[str, Any]:
        """Converts model to dictionary."""
        return EnterpriseIntelligenceSerializer.to_dict(model)

    @staticmethod
    def to_json(model: EnterpriseIntelligenceModel, indent: int = 2) -> str:
        """Serializes model to JSON string."""
        return EnterpriseIntelligenceSerializer.to_json(model, indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> EnterpriseIntelligenceModel:
        """Deserializes dictionary into model."""
        return EnterpriseIntelligenceSerializer.from_dict(data)

    @staticmethod
    def from_json(json_str: str) -> EnterpriseIntelligenceModel:
        """Deserializes JSON string into model."""
        return EnterpriseIntelligenceSerializer.from_json(json_str)

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Returns metrics collector snapshot."""
        return self._metrics.get_snapshot()

    @staticmethod
    def version() -> Dict[str, str]:
        """Returns version details for Platform 2."""
        return {
            "schema_version": "1.0.0",
            "platform_version": "1.0.0",
            "subsystem": "akaal.intelligence",
        }

    @staticmethod
    def health() -> Dict[str, Any]:
        """Returns health status of Platform 2."""
        return {
            "status": "HEALTHY",
            "subsystem": "akaal.intelligence",
            "version": "1.0.0",
        }

    @staticmethod
    def supported_features() -> List[str]:
        """Returns list of supported features in Platform 2."""
        return [
            "AgentCoordinationPlan",
            "StrategySynthesis",
            "RecommendationAggregation",
            "MigrationSimulationResult",
            "ReadinessAssessment",
            "DecisionGraphEngine",
            "MAUTConflictResolution",
            "LosslessDictJSONSerialization",
            "SHA256GovernanceChecksum",
        ]
