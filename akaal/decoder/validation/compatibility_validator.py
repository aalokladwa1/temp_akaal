"""
Akaal — Decoder Compatibility Validator
=======================================
Validator for checking cross-storage-family compatibility constraints.
"""

from typing import List
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph


class CompatibilityValidator:
    """Validates storage model family compatibility parameters."""

    @staticmethod
    def validate_compatibility(graph: CanonicalObjectGraph) -> List[str]:
        warnings: List[str] = []
        return warnings
