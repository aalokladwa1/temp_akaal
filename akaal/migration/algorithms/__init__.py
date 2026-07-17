"""
Akaal — Algorithms Package
==========================
Consolidates all progression, safe-next, and bounds checker algorithms for identity migration.
"""

from akaal.migration.algorithms.progression import (
    IdentityProgressionEngine,
    IdentityOverflowError,
    CycleCollisionError,
)
from akaal.migration.algorithms.partition_bounds import (
    shift_value,
    normalize_interval,
)

__all__ = [
    "IdentityProgressionEngine",
    "IdentityOverflowError",
    "CycleCollisionError",
    "shift_value",
    "normalize_interval",
]
