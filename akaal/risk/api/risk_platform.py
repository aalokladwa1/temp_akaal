"""
Akaal — Risk Platform Public API
================================
Public API for enterprise database migration risk assessment.
Consumes exclusively CanonicalMigrationModel from Decoder and outputs RiskAssessmentModel.
Contains zero SQL generation, zero migration execution, zero planning, zero advisory execution.
"""

import time
import logging
from typing import Any, Dict, Optional

from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.risk.engine.normalization_engine import NormalizationEngine
from akaal.risk.registry.analyzer_registry import AnalyzerRegistry
from akaal.risk.metrics.risk_metrics import RiskMetrics

logger = logging.getLogger("akaal.risk")


class RiskPlatform:
    """
    Public entry point for Risk Platform.
    Analyzes CanonicalMigrationModel and outputs deterministic, immutable RiskAssessmentModel.
    """

    _registry: Optional[AnalyzerRegistry] = None

    @classmethod
    def get_registry(cls) -> AnalyzerRegistry:
        if cls._registry is None:
            cls._registry = AnalyzerRegistry(auto_register_defaults=True)
        return cls._registry

    @classmethod
    def assess_risk(
        cls,
        canonical_model: CanonicalMigrationModel,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessmentModel:
        t0 = time.time()
        metrics = RiskMetrics()

        ctx = RiskContext(
            canonical_model=canonical_model,
            configuration=configuration or {},
            simulation_mode=False,
        )

        engine = NormalizationEngine()
        model, trace = engine.analyze(ctx)

        t1 = time.time()
        metrics.record_analysis_time((t1 - t0) * 1000.0)

        return model

    @classmethod
    def simulate(
        cls,
        canonical_model: CanonicalMigrationModel,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = RiskContext(
            canonical_model=canonical_model,
            configuration=configuration or {},
            simulation_mode=True,
        )

        engine = NormalizationEngine()
        model, trace = engine.analyze(ctx)

        return {
            "simulation_mode": True,
            "overall_risk_score": model.overall_risk_score,
            "readiness": model.readiness,
            "total_risks_detected": len(model.risk_items),
        }


def assess_risk(
    canonical_model: CanonicalMigrationModel,
    configuration: Optional[Dict[str, Any]] = None,
) -> RiskAssessmentModel:
    """Top-level helper function for Risk Platform risk assessment."""
    return RiskPlatform.assess_risk(
        canonical_model=canonical_model,
        configuration=configuration,
    )
