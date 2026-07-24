"""Validation configuration definitions and pre-built enterprise profiles."""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class ValidationProfile(str, Enum):
    LIGHTWEIGHT = "LIGHTWEIGHT"
    BALANCED = "BALANCED"
    STRICT = "STRICT"
    ENTERPRISE_FINANCE = "ENTERPRISE_FINANCE"
    ENTERPRISE_HEALTHCARE = "ENTERPRISE_HEALTHCARE"
    CUSTOM = "CUSTOM"


class PolicyProfile(str, Enum):
    FINANCE = "FINANCE"
    HEALTHCARE = "HEALTHCARE"
    GOVERNMENT = "GOVERNMENT"
    DEV = "DEV"
    TEST = "TEST"


@dataclass
class ValidationConfig:
    """Configuration parameters for the validation platform."""

    profile: ValidationProfile = ValidationProfile.BALANCED
    policy_profile: PolicyProfile = PolicyProfile.DEV
    sample_rate: float = 1.0  # 1.0 = 100% full dataset validation
    max_parallel_workers: int = 4
    enable_merkle_tree: bool = True
    enable_cdc_validation: bool = True
    enable_lob_validation: bool = True
    enable_unicode_validation: bool = True
    enable_statistical_sampling: bool = True
    enable_explainability: bool = True
    enable_evidence_generation: bool = True
    enable_distributed_execution: bool = False
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    stop_on_first_failure: bool = False
    confidence_threshold: float = 95.0
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)
