"""
Akaal — Advanced-Object Conversion Service Boundary API
========================================================
Defines the public interfaces, request/response models, and compatibility
scorecards for advanced database object conversion.
"""

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional, Any
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import ConversionContext
from akaal.core.conversion.api.diagnostics import Diagnostic

class ObjectCompatibilityTier(str, Enum):
    NATIVE = "NATIVE"
    EMULATED = "EMULATED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"

class ConfidenceDimension(str, Enum):
    PARSER = "PARSER"
    SEMANTIC = "SEMANTIC"
    DEPENDENCY = "DEPENDENCY"
    RENDERER = "RENDERER"
    VALIDATION = "VALIDATION"

class CertificationDisposition(str, Enum):
    CERTIFIED = "CERTIFIED"
    BLOCKED = "BLOCKED"
    REQUIRES_MANUAL_SIGN_OFF = "REQUIRES_MANUAL_SIGN_OFF"

class ManualReviewReason(str, Enum):
    UNRESOLVED_DEPENDENCY = "UNRESOLVED_DEPENDENCY"
    COMPLEX_TRANSACTION_BLOCK = "COMPLEX_TRANSACTION_BLOCK"
    UNSAFE_MUTATION_PATTERN = "UNSAFE_MUTATION_PATTERN"
    NON_DETERMINISTIC_MV_REFRESH = "NON_DETERMINISTIC_MV_REFRESH"

@dataclass(frozen=True)
class ConfidenceEvidence:
    dimension: ConfidenceDimension
    score: float  # 0.0 to 1.0
    evidence_log: Tuple[str, ...]

@dataclass(frozen=True)
class ObjectCompatibilityReport:
    target_object_name: str
    compatibility_tier: ObjectCompatibilityTier
    dimensions: Tuple[ConfidenceEvidence, ...]
    disposition: CertificationDisposition
    manual_review_reasons: Tuple[ManualReviewReason, ...]

class RollbackActionKind(str, Enum):
    DROP_PROCEDURE = "DROP_PROCEDURE"
    RESTORE_PRE_MIGRATION_DEFINITION = "RESTORE_PRE_MIGRATION_DEFINITION"
    RESTORE_PRIVILEGES = "RESTORE_PRIVILEGES"
    UNSAFE_ABORT = "UNSAFE_ABORT"

@dataclass(frozen=True)
class RoutineRollbackPlan:
    action_type: RollbackActionKind
    target_object_name: str
    rollback_sql_template: str
    pre_migration_definition_hash: Optional[str] = None
    original_privilege_grants: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ConversionRequest:
    source_ddl: str
    source_dialect: SystemType
    target_dialect: SystemType
    context: ConversionContext

@dataclass(frozen=True)
class ConversionResponse:
    target_sql: str
    rollback_plan: RoutineRollbackPlan
    compatibility_report: ObjectCompatibilityReport
    success: bool
    diagnostics: Tuple[Diagnostic, ...]

class IProcedureConversionService(abc.ABC):
    """Abstract interface governing the stored procedure compilation service."""

    @abc.abstractmethod
    def convert_procedure(self, request: ConversionRequest) -> ConversionResponse:
        """Parses, analyzes, plans, and renders stored procedures across database systems."""
        pass
