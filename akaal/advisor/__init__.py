"""
Akaal — Advisor Platform
========================
Enterprise advisory subsystem for converting MigrationExecutionPlan into MigrationAdvisoryModel.
Pure compiler architecture: immutable inputs, deterministic execution, immutable outputs.
"""

from akaal.advisor.api.advisor_platform import AdvisorPlatform
from akaal.advisor.models import (
    AdvisoryCategory,
    AdvisoryContext,
    AdvisoryDecision,
    AdvisoryEvent,
    AdvisoryEvidence,
    AdvisoryManifest,
    AdvisoryPriority,
    AdvisoryRecommendation,
    AdvisorySeverity,
    AdvisoryTrace,
    AdvisoryVersion,
    MigrationAdvisoryModel,
)

__version__ = "1.0.0"

__all__ = [
    "AdvisorPlatform",
    "MigrationAdvisoryModel",
    "AdvisoryRecommendation",
    "AdvisoryContext",
    "AdvisoryEvidence",
    "AdvisoryDecision",
    "AdvisorySeverity",
    "AdvisoryPriority",
    "AdvisoryCategory",
    "AdvisoryManifest",
    "AdvisoryTrace",
    "AdvisoryEvent",
    "AdvisoryVersion",
]
