"""
Akaal — Advisory Enums
=======================
Strict, immutable enums defining categories, severities, and priorities for recommendations.
"""

from enum import Enum, unique


@unique
class AdvisorySeverity(str, Enum):
    """Enumeration of advisory recommendation severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

    @property
    def rank(self) -> int:
        """Numerical rank for deterministic sorting (lower is higher severity)."""
        ranks = {
            AdvisorySeverity.CRITICAL: 0,
            AdvisorySeverity.HIGH: 1,
            AdvisorySeverity.MEDIUM: 2,
            AdvisorySeverity.LOW: 3,
            AdvisorySeverity.INFORMATIONAL: 4,
        }
        return ranks[self]


@unique
class AdvisoryPriority(str, Enum):
    """Enumeration of advisory recommendation priority levels."""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

    @property
    def rank(self) -> int:
        """Numerical rank for deterministic sorting (lower is higher priority)."""
        ranks = {
            AdvisoryPriority.P0: 0,
            AdvisoryPriority.P1: 1,
            AdvisoryPriority.P2: 2,
            AdvisoryPriority.P3: 3,
            AdvisoryPriority.P4: 4,
        }
        return ranks[self]


@unique
class AdvisoryCategory(str, Enum):
    """Enumeration of advisory recommendation domain categories."""
    STRATEGY = "STRATEGY"
    TOPOLOGY = "TOPOLOGY"
    WORKER = "WORKER"
    BATCHING = "BATCHING"
    CHECKPOINT = "CHECKPOINT"
    ROLLBACK = "ROLLBACK"
    HARDWARE = "HARDWARE"
    COST = "COST"
    ETA = "ETA"
    BEST_PRACTICE = "BEST_PRACTICE"
    PARALLELISM = "PARALLELISM"
    RESOURCE = "RESOURCE"
