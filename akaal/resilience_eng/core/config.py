"""Resilience Configuration and Profiles for Platform 5."""

from enum import Enum
from dataclasses import dataclass, field


class ResilienceEngProfile(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    FINANCE = "FINANCE"
    HEALTHCARE = "HEALTHCARE"
    GOVERNMENT = "GOVERNMENT"
    ENTERPRISE = "ENTERPRISE"


@dataclass
class ResilienceEngConfig:
    """Enterprise Configuration for Platform 5 Resilience Engineering Platform."""

    profile: ResilienceEngProfile = ResilienceEngProfile.ENTERPRISE
    enable_sandbox_isolation: bool = True
    enable_digital_twin_simulation: bool = True
    enable_policy_validation: bool = True
    enable_auto_recovery_validation: bool = True
    max_blast_radius_scope: str = "Service"
    default_confidence_threshold: float = 85.0
    max_parallel_experiments: int = 16
