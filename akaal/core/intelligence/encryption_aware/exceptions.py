"""
Akaal — Encryption Exception Taxonomy
=====================================
Defines exceptions for the Encryption-Aware Migration Platform.
"""

from akaal.core.intelligence.common.exceptions import AkaalIntelligenceError

class EncryptionOptimizationError(AkaalIntelligenceError):
    """Base exception for all encryption-aware migration planning failures."""
    pass

class EncryptionValidationError(EncryptionOptimizationError):
    """Raised when encryption configuration or schema layouts violate constraints."""
    pass

class EncryptionTranslationError(EncryptionOptimizationError):
    """Raised when translation paths or algorithm negotiations cannot be resolved."""
    pass

class EncryptionRegistryConflictError(EncryptionOptimizationError):
    """Raised when duplicate or conflicting rules are registered."""
    pass

class EncryptionPluginLoadError(EncryptionOptimizationError):
    """Raised when a dynamic encryption plugin fails validator checks."""
    pass
