"""
akaalEngine.extensions
======================
Authority #2: Extensions Authority for akaalEngine.
The single cross-authority provider-extension foundation for the reconstructed AKAAL Engine.
Owns provider identity, versioning, strategy registration, dependency truth, capability proof metadata,
configuration schemas, and drain-safe strategy resolution across all Engine authorities.
"""

from akaalEngine.extensions.authority import (
    ExtensionsAuthority,
    default_extensions_authority,
)

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

from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
    default_contract_registry,
)

from akaalEngine.extensions.spi.provider_bundle import (
    ProviderBundle,
)

from akaalEngine.extensions.spi.strategy_factory import (
    InstanceStrategyFactory,
    LazyTypeStrategyFactory,
    StrategyFactory,
)

from akaalEngine.extensions.resolution.handles import (
    ResolvedStrategyHandle,
)

from akaalEngine.extensions.errors.taxonomy import (
    AmbiguousStrategyError,
    AuthorityContractMismatchError,
    ConfigurationValidationError,
    DependencyResolutionError,
    ExtensionConflictError,
    ExtensionEngineException,
    ExtensionHandleLeakError,
    ExtensionLoadingError,
    ExtensionNotFoundError,
    ExtensionRegistrationError,
    IncompatibleEngineVersionError,
    LifecycleTransitionError,
    ProviderNotFoundError,
    StrategyNotFoundError,
)

__all__ = [
    # Canonical Façade
    "ExtensionsAuthority",
    "default_extensions_authority",
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
    "ProviderBundle",
    # Sanitized DTOs
    "SanitizedConfigurationField",
    "SanitizedConfigurationSchema",
    "SanitizedStrategyDescriptor",
    "SanitizedProviderDescriptor",
    "SanitizedExtensionDescriptor",
    # SPI & Contracts
    "AuthorityContractDefinition",
    "AuthorityContractRegistry",
    "default_contract_registry",
    "StrategyFactory",
    "InstanceStrategyFactory",
    "LazyTypeStrategyFactory",
    # Resolution
    "ResolvedStrategyHandle",
    # Errors
    "ExtensionEngineException",
    "ExtensionRegistrationError",
    "ExtensionConflictError",
    "ExtensionNotFoundError",
    "ProviderNotFoundError",
    "StrategyNotFoundError",
    "AmbiguousStrategyError",
    "AuthorityContractMismatchError",
    "IncompatibleEngineVersionError",
    "DependencyResolutionError",
    "ConfigurationValidationError",
    "LifecycleTransitionError",
    "ExtensionHandleLeakError",
    "ExtensionLoadingError",
]
