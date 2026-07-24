"""Reliability Configuration and Operational Profiles."""

from enum import Enum
from dataclasses import dataclass, field


class ReliabilityProfile(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    STRICT_FINANCE = "STRICT_FINANCE"
    STRICT_HEALTHCARE = "STRICT_HEALTHCARE"
    GOVERNMENT = "GOVERNMENT"
    ENTERPRISE = "ENTERPRISE"


@dataclass
class ReliabilityConfig:
    """Enterprise Configuration for Platform 4 Reliability Platform."""

    profile: ReliabilityProfile = ReliabilityProfile.ENTERPRISE
    max_retries: int = 5
    retry_budget_max: int = 100
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_reset_sec: float = 10.0
    bulkhead_max_concurrent_calls: int = 50
    enable_adaptive_load_shedding: bool = True
    enable_auto_healing: bool = True
    max_parallel_workers: int = 16
