"""
akaalEngine.extensions.errors.taxonomy
======================================
Structured exception taxonomy for Authority #2 Extensions.
All exceptions derive from ExtensionEngineException and carry typed diagnostic metadata.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class ExtensionEngineException(Exception):
    """Root base exception for all Extensions Authority errors."""
    def __init__(
        self,
        message: str,
        error_code: str = "EXTENSION_ERROR",
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class ExtensionRegistrationError(ExtensionEngineException):
    """Raised when extension registration validation or atomic publication fails."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="EXTENSION_REGISTRATION_FAILED", details=details)


class ExtensionConflictError(ExtensionEngineException):
    """Raised when duplicate or conflicting extension/provider/strategy ownership is detected."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="EXTENSION_CONFLICT", details=details)


class ExtensionNotFoundError(ExtensionEngineException):
    """Raised when a requested extension ID is not registered."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="EXTENSION_NOT_FOUND", details=details)


class ProviderNotFoundError(ExtensionEngineException):
    """Raised when a requested provider ID is not registered."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="PROVIDER_NOT_FOUND", details=details)


class StrategyNotFoundError(ExtensionEngineException):
    """Raised when no strategy matching criteria can be resolved."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="STRATEGY_NOT_FOUND", details=details)


class AmbiguousStrategyError(ExtensionEngineException):
    """Raised when multiple competing strategies match resolution criteria without explicit selection priority."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="STRATEGY_RESOLUTION_AMBIGUOUS", details=details)


class AuthorityContractMismatchError(ExtensionEngineException):
    """Raised when a strategy does not conform to the expected authority contract interface."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="AUTHORITY_CONTRACT_MISMATCH", details=details)


class IncompatibleEngineVersionError(ExtensionEngineException):
    """Raised when extension SemVer requirements do not match current engine version."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="ENGINE_VERSION_INCOMPATIBLE", details=details)


class DependencyResolutionError(ExtensionEngineException):
    """Raised when mandatory dependencies for an extension or provider are missing or invalid."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="DEPENDENCY_RESOLUTION_FAILED", details=details)


class ConfigurationValidationError(ExtensionEngineException):
    """Raised when configuration values violate schema constraints or field requirements."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="CONFIGURATION_VALIDATION_FAILED", details=details)


class LifecycleTransitionError(ExtensionEngineException):
    """Raised when an illegal lifecycle state machine transition is attempted."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="LIFECYCLE_TRANSITION_ILLEGAL", details=details)


class ExtensionHandleLeakError(ExtensionEngineException):
    """Raised when an extension operation violates active handle lease invariants."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="EXTENSION_HANDLE_LEAK", details=details)


class ExtensionLoadingError(ExtensionEngineException):
    """Raised when loading an extension module or entry point fails."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="EXTENSION_LOADING_FAILED", details=details)
