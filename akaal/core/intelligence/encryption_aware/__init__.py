"""
Akaal — Encryption-Aware Migration Subsystem
============================================
Defines capability analysis interfaces, translation engines, and validators for securing schemas.
"""

import abc
from akaal.core.comparison.models import Schema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.models import EncryptionReport

class IEncryptionAnalyzer(abc.ABC):
    """Abstract interface defining target TDE and key exchange mappings validation."""
    @abc.abstractmethod
    def analyze_encryption(self, schema: Schema, target_dialect: SystemType) -> EncryptionReport:
        pass

from akaal.core.intelligence.encryption_aware.exceptions import (
    EncryptionOptimizationError,
    EncryptionValidationError,
    EncryptionTranslationError,
    EncryptionRegistryConflictError,
    EncryptionPluginLoadError,
)

from akaal.core.intelligence.encryption_aware.models import (
    EncryptionAlgorithm,
    EncryptionMode,
    KeyManagementProvider,
    KeyRotationPolicy,
    EncryptionCompatibilityTier,
    EncryptionProfile,
    EncryptionCapability,
    EncryptionRule,
    EncryptionScore,
    EncryptionRecommendation,
    EncryptionTranslation,
    EncryptionStatistics,
    EncryptionSummary,
    EncryptionReport,
)

from akaal.core.intelligence.encryption_aware.registry import (
    EncryptionRuleMatcher,
    EncryptionStrategyRegistry,
)

from akaal.core.intelligence.encryption_aware.cache import (
    EnterpriseEncryptionCache,
)

from akaal.core.intelligence.encryption_aware.analyzer import (
    EncryptionTranslationGraph,
    EncryptionLayoutAnalyzer,
)

from akaal.core.intelligence.encryption_aware.validator import (
    EncryptionLayoutValidator,
)

from akaal.core.intelligence.encryption_aware.recommendation import (
    EncryptionScoreCalculator,
    EncryptionRanker,
    EncryptionRecommendationAdvisor,
)

from akaal.core.intelligence.encryption_aware.report import (
    EncryptionReportBuilder,
)

from akaal.core.intelligence.encryption_aware.metrics import (
    EncryptionMetricsCollector,
    SubsystemTimer,
)

__all__ = [
    "IEncryptionAnalyzer",
    "EncryptionAlgorithm",
    "EncryptionMode",
    "KeyManagementProvider",
    "KeyRotationPolicy",
    "EncryptionCompatibilityTier",
    "EncryptionProfile",
    "EncryptionCapability",
    "EncryptionRule",
    "EncryptionScore",
    "EncryptionRecommendation",
    "EncryptionTranslation",
    "EncryptionStatistics",
    "EncryptionSummary",
    "EncryptionReport",
    "EncryptionRuleMatcher",
    "EncryptionStrategyRegistry",
    "EnterpriseEncryptionCache",
    "EncryptionTranslationGraph",
    "EncryptionLayoutAnalyzer",
    "EncryptionLayoutValidator",
    "EncryptionScoreCalculator",
    "EncryptionRanker",
    "EncryptionRecommendationAdvisor",
    "EncryptionReportBuilder",
    "EncryptionMetricsCollector",
    "SubsystemTimer",
    "EncryptionOptimizationError",
    "EncryptionValidationError",
    "EncryptionTranslationError",
    "EncryptionRegistryConflictError",
    "EncryptionPluginLoadError",
]
