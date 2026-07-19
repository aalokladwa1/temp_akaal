"""
AKAAL Enterprise Intelligence Platform — Enumerations
=====================================================
Defines strategic enumerations for decision priorities, strategy types, readiness tiers,
and simulation confidence categories.
"""

from enum import Enum, unique


@unique
class DecisionPriority(str, Enum):
    """Priority level for synthesized enterprise migration decisions."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OPTIONAL = "OPTIONAL"


@unique
class StrategyType(str, Enum):
    """Enterprise migration execution strategy archetype."""
    AGGRESSIVE_PARALLEL = "AGGRESSIVE_PARALLEL"
    BALANCED_STAGE_BY_STAGE = "BALANCED_STAGE_BY_STAGE"
    HIGH_AVAILABILITY_CUTOVER = "HIGH_AVAILABILITY_CUTOVER"
    CONSERVATIVE_SEQUENTIAL = "CONSERVATIVE_SEQUENTIAL"
    CUSTOM_HYBRID = "CUSTOM_HYBRID"


@unique
class ReadinessTier(str, Enum):
    """Enterprise cutover readiness classification tier."""
    PRODUCTION_READY = "PRODUCTION_READY"
    READY_WITH_CONDITIONS = "READY_WITH_CONDITIONS"
    REQUIRES_REMEDIATION = "REQUIRES_REMEDIATION"
    NOT_READY = "NOT_READY"


@unique
class RiskLevel(str, Enum):
    """Enterprise strategic risk level."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEGLIGIBLE = "NEGLIGIBLE"
