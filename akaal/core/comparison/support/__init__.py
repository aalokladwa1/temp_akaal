"""
Akaal — Comparison Support Utilities
====================================
Consolidates and exports all database-agnostic parsing, normalization, and resolving methods.
"""

from akaal.core.comparison.support.type_normalizer import normalize_data_type
from akaal.core.comparison.support.default_normalizer import normalize_default_value
from akaal.core.comparison.support.equivalence_rules import (
    are_types_equivalent,
    are_defaults_equivalent,
)
from akaal.core.comparison.support.identifier_resolver import resolve_identifier

__all__ = [
    "normalize_data_type",
    "normalize_default_value",
    "are_types_equivalent",
    "are_defaults_equivalent",
    "resolve_identifier",
]
