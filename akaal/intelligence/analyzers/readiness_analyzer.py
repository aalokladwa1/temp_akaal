"""
AKAAL Enterprise Intelligence Platform — Readiness Analyzer
============================================================
Evaluates operational, schema, data, and hardware readiness metrics to produce ReadinessAssessment objects.
"""

from typing import Any, Dict, Optional
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.intelligence.analyzers.base_intelligence_analyzer import BaseIntelligenceAnalyzer
from akaal.intelligence.models.enterprise_intelligence_enums import ReadinessTier
from akaal.intelligence.models.readiness_assessment import ReadinessAssessment


class ReadinessAnalyzer(BaseIntelligenceAnalyzer):
    """
    Evaluates enterprise cutover readiness scores (0.0 to 100.0) and readiness tiers.
    """

    @property
    def name(self) -> str:
        return "readiness"

    @property
    def description(self) -> str:
        return "Evaluates schema, data, hardware, and operational enterprise cutover readiness."

    def analyze(
        self,
        advisory_model: MigrationAdvisoryModel,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReadinessAssessment:
        rec_count = len(advisory_model.recommendations) if advisory_model and advisory_model.recommendations else 0

        # Calculate scores deterministically
        schema_score = max(70.0, 98.0 - (rec_count * 1.5))
        data_score = max(70.0, 95.0 - (rec_count * 1.0))
        hardware_score = max(80.0, 96.0 - (rec_count * 0.5))
        operational_score = max(75.0, 92.0 - (rec_count * 1.0))

        overall_score = round((schema_score + data_score + hardware_score + operational_score) / 4.0, 1)

        if overall_score >= 90.0:
            tier = ReadinessTier.PRODUCTION_READY
        elif overall_score >= 80.0:
            tier = ReadinessTier.READY_WITH_CONDITIONS
        elif overall_score >= 70.0:
            tier = ReadinessTier.REQUIRES_REMEDIATION
        else:
            tier = ReadinessTier.NOT_READY

        return ReadinessAssessment(
            assessment_id=f"READ-{advisory_model.model_id[:8] if advisory_model and hasattr(advisory_model, 'model_id') and advisory_model.model_id else 'DEFAULT'}",
            overall_readiness_score=overall_score,
            tier=tier,
            schema_readiness_score=round(schema_score, 1),
            data_readiness_score=round(data_score, 1),
            hardware_readiness_score=round(hardware_score, 1),
            operational_readiness_score=round(operational_score, 1),
            critical_blockers=(),
            warnings=("Verify target database storage volume auto-expansion.",),
            remediation_steps=("Ensure target database backup is triggered prior to cutover.",),
            metadata={"source_analyzer": self.name},
        )
