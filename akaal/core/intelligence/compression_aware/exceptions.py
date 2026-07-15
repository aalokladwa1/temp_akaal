"""
Akaal — Compression-Aware Subsystem Exceptions
==============================================
Exception hierarchy for compression parsing, negotiation, and strategy registries.
"""

from akaal.core.intelligence.common.exceptions import AkaalIntelligenceError


class CompressionOptimizationError(AkaalIntelligenceError):
    """Base exception for all compression-aware migration planning failures."""
    pass


class CompressionValidationError(CompressionOptimizationError):
    """Raised when compression properties or schemas fail validation constraints."""
    pass


class CompressionTranslationError(CompressionOptimizationError):
    """Raised when translating compression options between source and target engines fails."""
    pass


class CompressionRegistryConflictError(CompressionOptimizationError):
    """Raised on strategy registration duplicates or dialect overlap conflicts."""
    pass


class CompressionPluginLoadError(CompressionOptimizationError):
    """Raised when dynamic third-party compression adapters fail loading or validation checks."""
    pass
