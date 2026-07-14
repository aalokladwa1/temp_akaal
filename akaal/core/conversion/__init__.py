"""
Akaal — Type Conversion Subsystem
=================================
Provides version-aware, database-agnostic type conversion and mapping capabilities.
"""

from akaal.core.conversion.exceptions import (
    ConversionError,
    ValidationFailure,
    UnsupportedCapability,
    PolicyViolation,
    RegistryError,
    PluginLoadError,
    EngineInternalError,
    UnsupportedVendorError,
    VersionIncompatibility,
)

from akaal.core.conversion.api.models import (
    TypeCategory,
    ConversionStatus,
    DbVersion,
    DataType,
    ConversionPolicy,
    ConversionContext,
    SpatialMetadata,
)

from akaal.core.conversion.api.diagnostics import (
    DiagnosticSeverity,
    DiagnosticCategory,
    RecommendationCategory,
    StructuredRecommendation,
    Diagnostic,
)

from akaal.core.conversion.api.observers import (
    ConversionObserver,
)

from akaal.core.conversion.internal.normalizer import (
    TypeNormalizer,
)

from akaal.core.conversion.internal.capabilities import (
    CapabilityType,
    NegotiationLevel,
    EmulationSpec,
    VendorCapability,
    CapabilityMatrix,
    ICapabilityProvider,
    DefaultCapabilityProvider,
)

from akaal.core.conversion.internal.rules import (
    RuleMetadata,
    ConversionRule,
    DeclarativeConversionRule,
)

from akaal.core.conversion.internal.registry import (
    IRuleRegistry,
    RegistrySnapshot,
    ThreadSafeRuleRegistry,
)

from akaal.core.conversion.internal.scoring import (
    ConfidenceBreakdown,
    ConfidenceScoringEngine,
)

from akaal.core.conversion.internal.engine import (
    TraceStep,
    ConversionTrace,
    ConversionResult,
    TypeConversionEngine,
)
