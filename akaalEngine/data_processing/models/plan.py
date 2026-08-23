"""
akaalEngine.data_processing.models.plan
========================================
Immutable ProcessingPlan, TransformationRule, LookupDefinition, and policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Dict, Mapping, Optional, Sequence

from akaalEngine.data_processing.models.ast import ASTNode


class RuleType(str, Enum):
    MAPPING = "MAPPING"
    CLEANSING = "CLEANSING"
    EXPRESSION = "EXPRESSION"
    PRIVACY = "PRIVACY"
    LOOKUP = "LOOKUP"
    DEFAULT = "DEFAULT"
    CUSTOM_HOOK = "CUSTOM_HOOK"


class MalformedDataPolicy(str, Enum):
    FAIL_JOB = "FAIL_JOB"
    REJECT_RECORD = "REJECT_RECORD"
    QUARANTINE_RECORD = "QUARANTINE_RECORD"
    USE_DEFAULT = "USE_DEFAULT"
    USE_NULL = "USE_NULL"


class PrivacyStrategy(str, Enum):
    STATIC_REDACT = "STATIC_REDACT"
    PARTIAL_MASK = "PARTIAL_MASK"
    NULLIFY = "NULLIFY"
    HASH = "HASH"
    KEYED_PSEUDONYM = "KEYED_PSEUDONYM"
    FORMAT_PRESERVING_MASK = "FORMAT_PRESERVING_MASK"


@dataclass(frozen=True)
class LookupDefinition:
    """Lookup table definition."""
    lookup_name: str
    key_column: str
    value_column: str
    mapping_data: Mapping[Any, Any] = field(default_factory=dict)
    missing_key_policy: str = "USE_NULL"  # USE_NULL, USE_DEFAULT, QUARANTINE_RECORD


@dataclass(frozen=True)
class TransformationRule:
    """Single transformation rule."""
    rule_id: str
    column_name: str
    rule_type: RuleType
    priority: int = 100
    target_column_name: Optional[str] = None
    expression_ast: Optional[ASTNode] = None
    default_value: Any = None
    privacy_strategy: Optional[PrivacyStrategy] = None
    privacy_key_ref: Optional[str] = None
    mask_char: str = "*"
    unmasked_length: int = 4
    cleansing_operation: Optional[str] = None  # TRIM, UPPER, LOWER, REPLACE
    lookup_definition: Optional[LookupDefinition] = None
    malformed_policy: MalformedDataPolicy = MalformedDataPolicy.QUARANTINE_RECORD


@dataclass(frozen=True)
class ProcessingPlan:
    """
    Immutable compiled processing plan.
    Computed once per dataset/object and includes deterministic SHA-256 fingerprint.
    Excludes raw secret key material from fingerprinting.
    """
    object_name: str
    compiled_rules: Sequence[TransformationRule] = field(default_factory=tuple)
    execution_order: Sequence[str] = field(default_factory=tuple)
    filter_predicate: Optional[ASTNode] = None
    dedup_key_columns: Sequence[str] = field(default_factory=tuple)
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            raw_repr = {
                "object_name": self.object_name,
                "execution_order": list(self.execution_order),
                "rules_count": len(self.compiled_rules),
                "dedup_keys": list(self.dedup_key_columns),
            }
            h = hashlib.sha256(json.dumps(raw_repr, sort_keys=True).encode("utf-8")).hexdigest()
            object.__setattr__(self, "fingerprint", h)
