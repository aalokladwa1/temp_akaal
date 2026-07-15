"""
Akaal — Cross-Version Compatibility Subsystem
=============================================
Complete public interface for the Enterprise Cross-Version Compatibility Engine.

This subsystem provides:
- Dialect feature capability matrix evaluation
- Source-to-target compatibility tier resolution
- Deterministic rule-based override registry
- Structured diagnostics and scoring
- Immutable CompatibilityReport assembly

No SQL generation. No DDL output. No database writes.
Pure metadata analysis and planning only.
"""

import abc
from akaal.core.comparison.models import Schema
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import DbVersion
from akaal.core.intelligence.common.models import CompatibilityReport as _SharedCompatibilityReport


class ICompatibilityEngine(abc.ABC):
    """Abstract interface defining the schema version capability checks against capability matrices."""

    @abc.abstractmethod
    def check_compatibility(
        self,
        schema: Schema,
        target_dialect: SystemType,
        target_version: DbVersion,
    ) -> _SharedCompatibilityReport:
        pass


# Subsystem-specific models and components
from akaal.core.intelligence.cross_version.exceptions import (
    CompatibilityEngineError,
    CompatibilityRuleValidationError,
    CompatibilityRegistryConflictError,
    CapabilityMatrixError,
    VersionParseError,
)

from akaal.core.intelligence.cross_version.models import (
    CompatibilityTier,
    FeatureCategory,
    CompatibilityRuleAction,
    FeatureCapability,
    CompatibilityRule,
    CompatibilityScore,
    CompatibilityFinding,
    CompatibilityStatistics,
    CompatibilitySummary,
    CompatibilityReport,
)

from akaal.core.intelligence.cross_version.registry import (
    CompatibilityRuleMatcher,
    CompatibilityStrategyRegistry,
)

from akaal.core.intelligence.cross_version.cache import (
    CompatibilityCache,
)

from akaal.core.intelligence.cross_version.metrics import (
    CompatibilityMetricsCollector,
    CompatibilitySubsystemTimer,
)

from akaal.core.intelligence.cross_version.analyzer import (
    CompatibilityCapabilityAnalyzer,
    CrossVersionCompatibilityAnalyzer,
)

from akaal.core.intelligence.cross_version.validator import (
    CompatibilityRuleSetValidator,
    CompatibilityFindingAuditor,
)

from akaal.core.intelligence.cross_version.recommendation import (
    CompatibilityRecommendation,
    CompatibilityScoreCalculator,
    CompatibilityRanker,
    CompatibilityRecommendationAdvisor,
)

from akaal.core.intelligence.cross_version.report import (
    CompatibilityReportBuilder,
)

__all__ = [
    # Interface
    "ICompatibilityEngine",

    # Exceptions
    "CompatibilityEngineError",
    "CompatibilityRuleValidationError",
    "CompatibilityRegistryConflictError",
    "CapabilityMatrixError",
    "VersionParseError",

    # Models
    "CompatibilityTier",
    "FeatureCategory",
    "CompatibilityRuleAction",
    "FeatureCapability",
    "CompatibilityRule",
    "CompatibilityScore",
    "CompatibilityFinding",
    "CompatibilityStatistics",
    "CompatibilitySummary",
    "CompatibilityReport",

    # Registry
    "CompatibilityRuleMatcher",
    "CompatibilityStrategyRegistry",

    # Cache
    "CompatibilityCache",

    # Metrics
    "CompatibilityMetricsCollector",
    "CompatibilitySubsystemTimer",

    # Analyzers
    "CompatibilityCapabilityAnalyzer",
    "CrossVersionCompatibilityAnalyzer",

    # Validators
    "CompatibilityRuleSetValidator",
    "CompatibilityFindingAuditor",

    # Recommendations
    "CompatibilityRecommendation",
    "CompatibilityScoreCalculator",
    "CompatibilityRanker",
    "CompatibilityRecommendationAdvisor",

    # Report
    "CompatibilityReportBuilder",
]
