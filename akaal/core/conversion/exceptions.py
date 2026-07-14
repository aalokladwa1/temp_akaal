"""
Akaal — Type Conversion Exceptions
==================================
Houses the domain-specific structured exception hierarchy for the Type Conversion Engine.
"""

class ConversionError(Exception):
    """Base exception for all conversion engine operations."""
    pass


class ValidationFailure(ConversionError):
    """Raised when data type validation or input structure verification fails."""
    def __init__(self, errors: list[str], message: str = None):
        self.errors = errors
        msg = message or f"Validation failed: {'; '.join(errors)}"
        super().__init__(msg)


class UnsupportedCapability(ConversionError):
    """Raised when a requested capability is completely unsupported by the target database version."""
    def __init__(self, capability: str, target_vendor: str, target_version: str):
        self.capability = capability
        self.target_vendor = target_vendor
        self.target_version = target_version
        super().__init__(
            f"Capability '{capability}' is unsupported on target {target_vendor} (version {target_version})."
        )


class PolicyViolation(ConversionError):
    """Raised when a type conversion violates the safety policies configured in the engine."""
    def __init__(self, policy_key: str, message: str):
        self.policy_key = policy_key
        super().__init__(f"Policy violation [{policy_key}]: {message}")


class RegistryError(ConversionError):
    """Raised when a rule registration is malformed, duplicate, or conflicts with existing rules."""
    pass


class PluginLoadError(ConversionError):
    """Raised when an external plugin fails compatibility negotiation or initialization."""
    pass


class EngineInternalError(ConversionError):
    """Raised when internal compilation, cache indexing, or pipeline steps fail."""
    pass


class UnsupportedVendorError(ConversionError):
    """Raised when an unknown database vendor system is specified."""
    def __init__(self, vendor: str):
        self.vendor = vendor
        super().__init__(f"Database vendor '{vendor}' is not supported by the conversion engine.")


class VersionIncompatibility(ConversionError):
    """Raised when a database version is incompatible with required conversion procedures."""
    pass
