"""
akaalEngine.schema.mapping
==========================
Structural mapping engine, validation, and deterministic serialization.
"""

from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.mapping.serializer import MappingSerializer
from akaalEngine.schema.mapping.validator import (
    MappingDiagnostic,
    MappingValidationResult,
    MappingValidator,
)

__all__ = [
    "MappingEngine",
    "MappingSerializer",
    "MappingValidator",
    "MappingDiagnostic",
    "MappingValidationResult",
]
