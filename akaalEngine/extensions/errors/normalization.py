"""
akaalEngine.extensions.errors.normalization
==========================================
Normalizes external Python exceptions into structured ExtensionEngineException instances.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from akaalEngine.extensions.errors.sanitization import sanitize_error_message
from akaalEngine.extensions.errors.taxonomy import (
    ConfigurationValidationError,
    DependencyResolutionError,
    ExtensionConflictError,
    ExtensionEngineException,
    ExtensionLoadingError,
    ExtensionRegistrationError,
    IncompatibleEngineVersionError,
)


def normalize_extension_error(
    exc: Exception,
    stage: str = "EXECUTION",
    context: Optional[Mapping[str, Any]] = None,
) -> ExtensionEngineException:
    """Normalizes any Python exception into an ExtensionEngineException hierarchy."""
    if isinstance(exc, ExtensionEngineException):
        return exc

    raw_msg = sanitize_error_message(str(exc))
    details = dict(context or {})
    details["original_error_type"] = type(exc).__name__
    details["stage"] = stage

    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return DependencyResolutionError(
            f"Dependency missing or failed to import during {stage}: {raw_msg}",
            details=details,
        )

    if isinstance(exc, ValueError):
        return ConfigurationValidationError(
            f"Validation failure during {stage}: {raw_msg}",
            details=details,
        )

    if isinstance(exc, KeyError):
        return ExtensionEngineException(
            f"Resource key not found during {stage}: {raw_msg}",
            error_code="RESOURCE_KEY_NOT_FOUND",
            details=details,
        )

    return ExtensionEngineException(
        f"Unexpected extension failure during {stage}: {raw_msg}",
        error_code="EXTENSION_INTERNAL_ERROR",
        details=details,
    )
