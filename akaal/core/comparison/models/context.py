"""
Akaal — Comparison Context
==========================
Defines the ComparisonContext class which encapsulates the parameters and options
governing the schema comparison execution.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class ComparisonContext:
    """
    Configuration parameters for comparison execution.
    Encapsulates all options to prevent flag propagation in constructor signatures.
    Designed for immutability and future extensibility.
    """
    strict_type_checking: bool = True
    strict_length_precision: bool = True
    ignore_index_names: bool = True
    ignore_constraint_names: bool = True
    normalize_identifiers: bool = True  # case-folding and quote removal
    ignore_views: bool = False
    ignore_triggers: bool = False
    custom_type_equivalences: Dict[str, str] = field(default_factory=dict)
