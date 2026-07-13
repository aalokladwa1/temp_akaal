"""
Akaal — Comparison Summary
==========================
Defines the ComparisonSummary model class that captures metric statistics of schema differences.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonSummary:
    """
    Typed summary statistics for a comparison report.
    Replaces generic dictionaries to enforce type safety.
    """
    total_objects: int
    total_differences: int
    added: int
    removed: int
    modified: int
    info: int
    warning: int
    critical: int
