"""Core abstractions, context, models, and interfaces for AKAAL Self-Healing Platform."""

from akaal.healing.core.interfaces import (
    IHealer,
    IDomainHealer,
    IHealingService,
    IHealingPlugin,
    IHealingPolicy,
)
from akaal.healing.core.models import (
    HealingPlan,
    HealingResult,
    HealingStep,
    RepairAction,
    RollbackManifest,
    ConfidenceScore,
    HealingStatus,
    RepairOutcome,
)
from akaal.healing.core.config import HealingConfig, HealingProfile, ApprovalMode, SLAConfig
from akaal.healing.core.context import HealingContext
from akaal.healing.core.session import HealingSession
from akaal.healing.core.registry import HealerRegistry

__all__ = [
    "IHealer",
    "IDomainHealer",
    "IHealingService",
    "IHealingPlugin",
    "IHealingPolicy",
    "HealingPlan",
    "HealingResult",
    "HealingStep",
    "RepairAction",
    "RollbackManifest",
    "ConfidenceScore",
    "HealingStatus",
    "RepairOutcome",
    "HealingConfig",
    "HealingProfile",
    "ApprovalMode",
    "SLAConfig",
    "HealingContext",
    "HealingSession",
    "HealerRegistry",
]
