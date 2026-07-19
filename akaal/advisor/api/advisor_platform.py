"""
Akaal — Advisor Platform API
=============================
The single public entry facade for the Advisor Platform.
Hides internal subsystem complexity behind a clean, deterministic API.
"""

from typing import Any, Dict, List, Optional

from akaal.advisor.engine.advisor_engine import AdvisorEngine
from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.advisor.registry.advisor_registry import AdvisorRegistry
from akaal.advisor.reporting.advisor_report_builder import AdvisorReportBuilder
from akaal.advisor.serialization.advisor_serializer import AdvisorSerializer
from akaal.advisor.validation.advisor_validator import AdvisorValidator


class AdvisorPlatform:
    """Public Enterprise Facade for Advisor Platform."""

    def __init__(self, engine: Optional[AdvisorEngine] = None) -> None:
        self._engine = engine or AdvisorEngine()

    @classmethod
    def create_default(cls) -> "AdvisorPlatform":
        """Factory method to instantiate an AdvisorPlatform with default core analyzers registered."""
        AdvisorRegistry.register_defaults()
        return cls(engine=AdvisorEngine())

    def analyze(
        self,
        plan: Any,
        context: Optional[AdvisoryContext] = None,
        advisory_id: str = "ADV-001",
    ) -> MigrationAdvisoryModel:
        """
        Analyze an execution plan and return a MigrationAdvisoryModel.
        Pure transformation layer.
        """
        return self._engine.execute(plan=plan, context=context, advisory_id=advisory_id)

    @staticmethod
    def to_dict(model: MigrationAdvisoryModel) -> Dict[str, Any]:
        """Convert MigrationAdvisoryModel to dictionary."""
        return AdvisorSerializer.to_dict(model)

    @staticmethod
    def to_json(model: MigrationAdvisoryModel, indent: int = 2) -> str:
        """Convert MigrationAdvisoryModel to JSON string."""
        return AdvisorSerializer.to_json(model, indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> MigrationAdvisoryModel:
        """Reconstruct MigrationAdvisoryModel from dictionary."""
        return AdvisorSerializer.from_dict(data)

    @staticmethod
    def from_json(json_str: str) -> MigrationAdvisoryModel:
        """Reconstruct MigrationAdvisoryModel from JSON string."""
        return AdvisorSerializer.from_json(json_str)

    @staticmethod
    def to_technical_report(model: MigrationAdvisoryModel) -> str:
        """Generate a complete technical advisory markdown report."""
        return AdvisorReportBuilder.build_technical_report(model)

    @staticmethod
    def to_recommendation_report(model: MigrationAdvisoryModel) -> str:
        """Generate a recommendation breakdown report."""
        return AdvisorReportBuilder.build_recommendation_report(model)

    @staticmethod
    def to_engineering_summary(model: MigrationAdvisoryModel) -> str:
        """Generate an engineering summary string."""
        return AdvisorReportBuilder.build_engineering_summary(model)

    @staticmethod
    def validate(model: MigrationAdvisoryModel) -> List[str]:
        """Validate MigrationAdvisoryModel completeness and consistency."""
        return AdvisorValidator.validate_advisory_model(model)

    @staticmethod
    def verify_integrity(model: MigrationAdvisoryModel) -> bool:
        """Verify model SHA-256 checksum integrity."""
        return model.verify_checksum()

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics collected by Advisor Platform."""
        return self._engine.metrics_collector.get_summary()
