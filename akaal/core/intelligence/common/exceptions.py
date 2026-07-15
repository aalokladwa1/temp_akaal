"""
Akaal — Intelligence Exception Taxonomy
=======================================
Defines the complete exception hierarchy for the Migration Intelligence platform.
"""

from typing import Any, Dict, Optional

class AkaalIntelligenceError(Exception):
    """Base exception for all Migration Intelligence errors, containing structured diagnostic metadata."""
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        subsystem_id: Optional[str] = None,
        remediation_guidance: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.subsystem_id = subsystem_id
        self.remediation_guidance = remediation_guidance
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes exception details to a dictionary representation."""
        return {
            "error_class": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "subsystem_id": self.subsystem_id,
            "remediation_guidance": self.remediation_guidance,
            "details": self.details,
        }


# =============================================================================
# Subsystem Specific Exception Classes
# =============================================================================

class ConfigValidationError(AkaalIntelligenceError):
    """Raised when configuration resources violate schema constraints."""
    pass


class SchemaValidationError(AkaalIntelligenceError):
    """Raised when source or target database schemas fail internal parsing validations."""
    pass


class RegistryFrozenError(AkaalIntelligenceError):
    """Raised when attempting registration on a frozen registry instance."""
    pass


class RegistryDuplicateError(AkaalIntelligenceError):
    """Raised when duplicate identifiers are detected inside a registry."""
    pass


class ConflictResolutionError(AkaalIntelligenceError):
    """Raised when overlapping rules or strategies conflict during registry resolution."""
    pass


class ReplaySequenceError(AkaalIntelligenceError):
    """Raised when logs sequence gaps, duplicates, or LSN mismatches are found during simulation."""
    pass


class ReplayTimelineSplitError(AkaalIntelligenceError):
    """Raised when sequence timeline splits or forks are detected in the CDC stream representation."""
    pass


class CompatibilityCheckError(AkaalIntelligenceError):
    """Raised when critical dialect compatibility limits are violated."""
    pass


class StorageOptimizationError(AkaalIntelligenceError):
    """Raised when storage allocation or partition projection calculations fail."""
    pass


class CompressionTranslationError(AkaalIntelligenceError):
    """Raised when target compression formats are completely incompatible with source settings."""
    pass


class EncryptionHandshakeError(AkaalIntelligenceError):
    """Raised when key exchange, TLS tunnels, or TDE parameters fail validation checks."""
    pass


class ResourceLoadingError(AkaalIntelligenceError):
    """Raised when filesystem JSON files or configurations fail to load."""
    pass


class PluginLoadError(AkaalIntelligenceError):
    """Raised when plugin loading, registration, or dependency verification fails."""
    pass


class ObservabilityError(AkaalIntelligenceError):
    """Raised when observability logging context or telemetry contracts are violated."""
    pass


class RecommendationError(AkaalIntelligenceError):
    """Raised when recommendations engine rules fail during calculation or ranking."""
    pass
