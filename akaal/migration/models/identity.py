"""
Akaal — Identity Migration Domain Models
========================================
Defines the operational runtime state, compatibility, reseed, and plan models for Feature 1.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from akaal.core.comparison.models.exceptions import IdentityDifference


class IdentityStateConfidence(str, Enum):
    EXACT = "EXACT"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class GeneratorValueSemantics(str, Enum):
    LAST_EMITTED = "LAST_EMITTED"
    NEXT_TO_EMIT = "NEXT_TO_EMIT"
    STORED_COUNTER = "STORED_COUNTER"
    TABLE_NEXT_VALUE = "TABLE_NEXT_VALUE"


class GeneratorStateSource(str, Enum):
    SYSTEM_CATALOG = "SYSTEM_CATALOG"
    EXPLICIT_DATA = "EXPLICIT_DATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IdentityRuntimeState:
    current_generator_value: Optional[int]
    last_generated_value: Optional[int]
    restart_value: Optional[int]
    state_confidence: IdentityStateConfidence
    value_semantics: GeneratorValueSemantics


class IdentityCompatibilityClass(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    EMULATED_EQUIVALENT = "EMULATED_EQUIVALENT"
    EMULATED_NON_EQUIVALENT = "EMULATED_NON_EQUIVALENT"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True)
class IdentityCompatibilityResult:
    classification: IdentityCompatibilityClass
    differences: Tuple[IdentityDifference, ...]
    blocking: bool


@dataclass(frozen=True)
class IdentityReseedInput:
    target_value: int
    increment: int


@dataclass(frozen=True)
class IdentityReseedResult:
    applied_sql: str
    success: bool


class IdentityActionType(str, Enum):
    CREATE = "CREATE"
    ALTER = "ALTER"
    DROP = "DROP"
    RESEED = "RESEED"
    REBUILD = "REBUILD"


@dataclass(frozen=True)
class IdentityAction:
    action_type: IdentityActionType
    sql_commands: Tuple[str, ...]
    rollback_commands: Tuple[str, ...]


@dataclass(frozen=True)
class IdentityMigrationPlan:
    actions: Tuple[IdentityAction, ...]
    plan_hash: str


@dataclass(frozen=True)
class IdentityApprovalRequirement:
    requirement_id: str
    reason: str
    severity: str


@dataclass(frozen=True)
class IdentityCheckpointState:
    last_applied_step: int
    sequence_offsets: Tuple[int, ...]


@dataclass(frozen=True)
class IdentityExecutionResult:
    success: bool
    applied_steps: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IdentityDiscoveryEvidence:
    catalog_source: str
    raw_output: str


@dataclass(frozen=True)
class IdentityConsistencyEvidence:
    lsn_position: str
    source_checksum: str


@dataclass(frozen=True)
class IdentityReconstructionRequirement:
    staging_table_name: str
    original_table_name: str
    rebuild_sql: str
