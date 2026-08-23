"""
akaalEngine.extensions.errors
=============================
Typed error taxonomy, normalization, and sanitization for Authority #2 Extensions.
"""

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

from akaalEngine.extensions.errors.sanitization import (
    sanitize_error_message,
)

from akaalEngine.extensions.errors.normalization import (
    normalize_extension_error,
)

__all__ = [
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
    "sanitize_error_message",
    "normalize_extension_error",
]
