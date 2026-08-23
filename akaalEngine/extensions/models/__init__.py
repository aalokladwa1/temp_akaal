"""
akaalEngine.extensions.models
=============================
Strongly typed, immutable domain models and enums for Authority #2 Extensions.
"""

from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    RegistryGeneration,
    StrategyId,
    normalize_identifier,
)

from akaalEngine.extensions.models.enums import (
    ConfigurationFieldType,
    DependencyMatchMode,
    DependencyStatus,
    DependencyType,
    ExtensionLifecycleState,
    ExtensionOrigin,
    IsolationMode,
    ProofLevel,
    TrustTier,
)

from akaalEngine.extensions.models.compatibility import (
    CompatibilityRange,
    CompatibilityResult,
    CompatibilityStatus,
)

from akaalEngine.extensions.models.dependency import (
    DependencyDiagnostic,
    DependencyGroup,
    DependencyRequirement,
    ExecutableDependency,
    NativeDependency,
    PythonDependency,
)

from akaalEngine.extensions.models.configuration import (
    ConfigurationCondition,
    ConfigurationConstraint,
    ConfigurationField,
    ConfigurationSchema,
)

from akaalEngine.extensions.models.capability import (
    CapabilityDeclaration,
    CapabilityTruth,
)

from akaalEngine.extensions.models.proof import (
    CertificationReference,
    ProofReference,
)

from akaalEngine.extensions.models.lifecycle import (
    ExtensionLifecycleSnapshot,
    TransitionRecord,
)

from akaalEngine.extensions.models.events import (
    ExtensionEvent,
    ExtensionEventType,
)

from akaalEngine.extensions.models.availability import (
    ExtensionAvailability,
)

from akaalEngine.extensions.models.strategy import (
    StrategyContribution,
)

from akaalEngine.extensions.models.provider import (
    ProviderContribution,
)

from akaalEngine.extensions.models.extension import (
    ExtensionManifest,
)

from akaalEngine.extensions.models.sanitized import (
    SanitizedConfigurationField,
    SanitizedConfigurationSchema,
    SanitizedExtensionDescriptor,
    SanitizedProviderDescriptor,
    SanitizedStrategyDescriptor,
)

__all__ = [
    # Identity
    "ExtensionId",
    "ProviderId",
    "AuthorityId",
    "StrategyId",
    "RegistryGeneration",
    "normalize_identifier",
    # Enums
    "ExtensionOrigin",
    "TrustTier",
    "IsolationMode",
    "ExtensionLifecycleState",
    "ProofLevel",
    "DependencyType",
    "DependencyStatus",
    "DependencyMatchMode",
    "ConfigurationFieldType",
    # Compatibility
    "CompatibilityRange",
    "CompatibilityResult",
    "CompatibilityStatus",
    # Dependencies
    "DependencyRequirement",
    "PythonDependency",
    "NativeDependency",
    "ExecutableDependency",
    "DependencyGroup",
    "DependencyDiagnostic",
    # Configuration
    "ConfigurationConstraint",
    "ConfigurationCondition",
    "ConfigurationField",
    "ConfigurationSchema",
    # Capabilities & Proof
    "CapabilityDeclaration",
    "CapabilityTruth",
    "ProofReference",
    "CertificationReference",
    # Lifecycle & Events
    "TransitionRecord",
    "ExtensionLifecycleSnapshot",
    "ExtensionEventType",
    "ExtensionEvent",
    "ExtensionAvailability",
    # Bundles & Contributions
    "StrategyContribution",
    "ProviderContribution",
    "ExtensionManifest",
    # Sanitized DTOs
    "SanitizedConfigurationField",
    "SanitizedConfigurationSchema",
    "SanitizedStrategyDescriptor",
    "SanitizedProviderDescriptor",
    "SanitizedExtensionDescriptor",
]
