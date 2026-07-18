"""
Akaal — Normalization Validator
===============================
Validator for checking structural completeness of normalized CanonicalObjects.
"""

from typing import List
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph


class NormalizationValidator:
    """Validates structural normalization completeness."""

    @staticmethod
    def validate_normalization(graph: CanonicalObjectGraph) -> List[str]:
        warnings: List[str] = []
        if len(graph.get_all_objects()) == 0:
            warnings.append("Normalized object graph is empty.")
        return warnings
