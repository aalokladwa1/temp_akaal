"""
Akaal — Intelligence Shared Core Package
=========================================
Aggregates and exposes the core exceptions, models, registry frameworks,
plugin loaders, config decoders, and telemetries.
"""

from akaal.core.intelligence.common.exceptions import (
    AkaalIntelligenceError,
    ConfigValidationError,
    SchemaValidationError,
    RegistryFrozenError,
    RegistryDuplicateError,
    ConflictResolutionError,
    ReplaySequenceError,
    ReplayTimelineSplitError,
    CompatibilityCheckError,
    StorageOptimizationError,
    CompressionTranslationError,
    EncryptionHandshakeError,
    ResourceLoadingError,
    PluginLoadError,
    ObservabilityError,
    RecommendationError,
)

from akaal.core.intelligence.common.models import (
    Severity,
    DiagnosticCategory,
    Diagnostic,
    DiagnosticsSummary,
    RecommendationScore,
    Recommendation,
    PluginMetadata,
    ConfigMetadata,
    ReportMetadata,
    ReplayReport,
    StorageReport,
    CompressionReport,
    EncryptionReport,
    CompatibilityReport,
    RecommendationReport,
    IntelligenceReport,
)

from akaal.core.intelligence.common.observability import (
    TelemetryContext,
    MetricRecord,
    EventRecord,
    TimingRecord,
    ITelemetryExporter,
    MemoryTelemetryExporter,
    IIntelligenceObservability,
    IntelligenceObservabilityContext,
    TimingTracker,
)

from akaal.core.intelligence.common.registry import BaseRegistry
from akaal.core.intelligence.common.plugin import PluginState, IPlugin, PluginManager
from akaal.core.intelligence.common.config import ConfigResourceLoader

__all__ = [
    # Exceptions
    "AkaalIntelligenceError",
    "ConfigValidationError",
    "SchemaValidationError",
    "RegistryFrozenError",
    "RegistryDuplicateError",
    "ConflictResolutionError",
    "ReplaySequenceError",
    "ReplayTimelineSplitError",
    "CompatibilityCheckError",
    "StorageOptimizationError",
    "CompressionTranslationError",
    "EncryptionHandshakeError",
    "ResourceLoadingError",
    "PluginLoadError",
    "ObservabilityError",
    "RecommendationError",

    # Models & Reports
    "Severity",
    "DiagnosticCategory",
    "Diagnostic",
    "DiagnosticsSummary",
    "RecommendationScore",
    "Recommendation",
    "PluginMetadata",
    "ConfigMetadata",
    "ReportMetadata",
    "ReplayReport",
    "StorageReport",
    "CompressionReport",
    "EncryptionReport",
    "CompatibilityReport",
    "RecommendationReport",
    "IntelligenceReport",

    # Observability
    "TelemetryContext",
    "MetricRecord",
    "EventRecord",
    "TimingRecord",
    "ITelemetryExporter",
    "MemoryTelemetryExporter",
    "IIntelligenceObservability",
    "IntelligenceObservabilityContext",
    "TimingTracker",

    # Registries & Loaders
    "BaseRegistry",
    "PluginState",
    "IPlugin",
    "PluginManager",
    "ConfigResourceLoader",
]
