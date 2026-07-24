"""Core abstractions, context, models, configurations, and interfaces for AKAAL Validation Platform."""

from akaal.validation.core.interfaces import (
    IValidator,
    IDomainValidator,
    IService,
    IPlugin,
    IPolicy,
    ICache,
    IEventPublisher,
)
from akaal.validation.core.models import (
    ValidationResult,
    ValidationIssue,
    SeverityLevel,
    ExplainabilityContext,
    EvidencePackage,
    ValidationStatus,
)
from akaal.validation.core.config import ValidationConfig, ValidationProfile, PolicyProfile
from akaal.validation.core.context import ValidationContext
from akaal.validation.core.session import ValidationSession
from akaal.validation.core.registry import ValidatorRegistry

__all__ = [
    "IValidator",
    "IDomainValidator",
    "IService",
    "IPlugin",
    "IPolicy",
    "ICache",
    "IEventPublisher",
    "ValidationResult",
    "ValidationIssue",
    "SeverityLevel",
    "ExplainabilityContext",
    "EvidencePackage",
    "ValidationStatus",
    "ValidationConfig",
    "ValidationProfile",
    "PolicyProfile",
    "ValidationContext",
    "ValidationSession",
    "ValidatorRegistry",
]
