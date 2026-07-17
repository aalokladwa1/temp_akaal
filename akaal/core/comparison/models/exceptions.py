"""
Akaal — Comparison Exceptions
=============================
Defines the exception hierarchy for the Schema Comparison Engine.
"""


class AkaalComparisonError(Exception):
    """Base exception for all comparison-related errors."""
    pass


class InvalidSchemaError(AkaalComparisonError):
    """Raised when a schema violates structural integrity constraints."""
    pass


class NormalizationError(AkaalComparisonError):
    """Raised when raw dialect schema metadata conversion fails."""
    pass


class UnsupportedObjectTypeError(AkaalComparisonError):
    """Raised when encountering an unregistered schema object type."""
    pass


class SerializationError(AkaalComparisonError):
    """Raised when JSON encoding/decoding of a DifferenceReport fails."""
    pass


from dataclasses import dataclass

@dataclass(frozen=True)
class IdentityDifference:
    """
    Represents a specific structural mismatch in identity properties.
    """
    property_name: str
    source_value: str
    target_value: str
    severity: str
