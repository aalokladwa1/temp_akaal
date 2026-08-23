"""
akaalEngine.schema.assessment
=============================
Compatibility, lossiness, risk scoring, readiness gates, and capacity projections.
"""

from akaalEngine.schema.assessment.compatibility import (
    CompatibilityBreakdown,
    PreMigrationCompatibilityAssessor,
)
from akaalEngine.schema.assessment.lossiness import (
    LossinessAssessment,
    LossinessEngine,
    LossinessReasonCode,
)
from akaalEngine.schema.assessment.projection import (
    TableCapacityProjection,
    TargetCapacityReport,
    TargetCapacitySchemaProjection,
)
from akaalEngine.schema.assessment.readiness import (
    ReadinessGateReport,
    ReadinessStatus,
    SchemaReadinessGateProvider,
)
from akaalEngine.schema.assessment.risk import (
    RiskFactor,
    RiskLevel,
    StructuralRiskReport,
    StructuralRiskScorer,
)

__all__ = [
    "LossinessReasonCode",
    "LossinessAssessment",
    "LossinessEngine",
    "CompatibilityBreakdown",
    "PreMigrationCompatibilityAssessor",
    "RiskLevel",
    "RiskFactor",
    "StructuralRiskReport",
    "StructuralRiskScorer",
    "ReadinessStatus",
    "ReadinessGateReport",
    "SchemaReadinessGateProvider",
    "TableCapacityProjection",
    "TargetCapacityReport",
    "TargetCapacitySchemaProjection",
]
