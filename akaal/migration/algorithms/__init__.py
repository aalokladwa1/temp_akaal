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

__all__ = [
    "IdentityProgressionEngine",
    "IdentityOverflowError",
    "CycleCollisionError",
]
