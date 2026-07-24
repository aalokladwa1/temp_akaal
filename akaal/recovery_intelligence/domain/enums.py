"""
AKAAL Platform 10 — Recovery Intelligence Domain Enums.
"""

from enum import Enum


class RecoveryStrategyType(str, Enum):
    CHECKPOINT_RESUME = "CHECKPOINT_RESUME"
    ROLLBACK_AND_REPLAY = "ROLLBACK_AND_REPLAY"
    FAILOVER_SECONDARY = "FAILOVER_SECONDARY"
    FULL_RESTART = "FULL_RESTART"


class RecoveryReadinessState(str, Enum):
    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    NOT_READY = "NOT_READY"
