"""
Akaal — Cross-Version Compatibility Exception Taxonomy
======================================================
Defines exceptions for the Cross-Version Compatibility Engine subsystem.
"""

from akaal.core.intelligence.common.exceptions import AkaalIntelligenceError


class CompatibilityEngineError(AkaalIntelligenceError):
    """Base exception for all cross-version compatibility engine failures."""
    pass


class CompatibilityRuleValidationError(CompatibilityEngineError):
    """Raised when a compatibility rule fails structural or semantic validation."""
    pass


class CompatibilityRegistryConflictError(CompatibilityEngineError):
    """Raised when overlapping or conflicting compatibility rules are registered."""
    pass


class CapabilityMatrixError(CompatibilityEngineError):
    """Raised when capability matrix lookup fails or yields an ambiguous result."""
    pass


class VersionParseError(CompatibilityEngineError):
    """Raised when a version string cannot be parsed into a structured representation."""
    pass
