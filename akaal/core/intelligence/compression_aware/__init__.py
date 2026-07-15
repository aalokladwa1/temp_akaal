"""
Akaal — Compression-Aware Migration Subsystem
==============================================
Provides compression capability negotiation, strategy routing, sizing estimations,
scored optimization suggestions, and diagnostic audits.
"""

from akaal.core.intelligence.compression_aware.models import (
    CompressionAlgorithm,
    CompressionCompatibilityTier,
    CompressionProfile,
    CompressionCapability,
    CompressionRule,
    CompressionScore,
    CompressionRecommendation,
    CompressionTranslation,
    CompressionStatistics,
    CompressionSummary,
    CompressionReport,
)
from akaal.core.intelligence.compression_aware.registry import (
    CompressionRuleMatcher,
    CompressionStrategyRegistry,
)
from akaal.core.intelligence.compression_aware.cache import (
    EnterpriseCompressionCache,
)
from akaal.core.intelligence.compression_aware.recommendation import (
    CompressionScoreCalculator,
    CompressionRanker,
    CompressionRecommendationAdvisor,
)
from akaal.core.intelligence.compression_aware.analyzer import (
    ICompressionAnalyzer,
    CompressionEstimatorStrategy,
    DefaultCompressionEstimatorStrategy,
    VendorCompressionEstimatorStrategy,
    PluginCompressionEstimatorStrategy,
    CompressionTranslationGraph,
    CompressionLayoutAnalyzer,
)
from akaal.core.intelligence.compression_aware.validator import (
    CompressionLayoutValidator,
)
from akaal.core.intelligence.compression_aware.report import (
    CompressionReportBuilder,
)
from akaal.core.intelligence.compression_aware.metrics import (
    CompressionMetricsCollector,
    SubsystemTimer,
)
from akaal.core.intelligence.compression_aware.exceptions import (
    CompressionOptimizationError,
    CompressionValidationError,
    CompressionTranslationError,
    CompressionRegistryConflictError,
    CompressionPluginLoadError,
)

__all__ = [
    "CompressionAlgorithm",
    "CompressionCompatibilityTier",
    "CompressionProfile",
    "CompressionCapability",
    "CompressionRule",
    "CompressionScore",
    "CompressionRecommendation",
    "CompressionTranslation",
    "CompressionStatistics",
    "CompressionSummary",
    "CompressionReport",
    "CompressionRuleMatcher",
    "CompressionStrategyRegistry",
    "EnterpriseCompressionCache",
    "CompressionScoreCalculator",
    "CompressionRanker",
    "CompressionRecommendationAdvisor",
    "ICompressionAnalyzer",
    "CompressionEstimatorStrategy",
    "DefaultCompressionEstimatorStrategy",
    "VendorCompressionEstimatorStrategy",
    "PluginCompressionEstimatorStrategy",
    "CompressionTranslationGraph",
    "CompressionLayoutAnalyzer",
    "CompressionLayoutValidator",
    "CompressionReportBuilder",
    "CompressionMetricsCollector",
    "SubsystemTimer",
    "CompressionOptimizationError",
    "CompressionValidationError",
    "CompressionTranslationError",
    "CompressionRegistryConflictError",
    "CompressionPluginLoadError",
]
