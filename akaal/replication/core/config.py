"""Replication Configuration and Operational Profiles."""

from enum import Enum
from dataclasses import dataclass, field


class ReplicationProfile(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    STRICT_FINANCE = "STRICT_FINANCE"
    STRICT_HEALTHCARE = "STRICT_HEALTHCARE"
    GOVERNMENT = "GOVERNMENT"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"


class FailoverMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    SEMI_AUTOMATIC = "SEMI_AUTOMATIC"
    MANUAL = "MANUAL"


@dataclass
class ReplicationConfig:
    """Enterprise Configuration for Platform 3 Replication."""

    profile: ReplicationProfile = ReplicationProfile.AUTOMATIC
    failover_mode: FailoverMode = FailoverMode.AUTOMATIC
    enable_dry_run: bool = False
    enable_auto_failover: bool = True
    max_replication_lag_ms: float = 5000.0
    sync_interval_seconds: float = 1.0
    max_parallel_workers: int = 16
    conflict_strategy: str = "LAST_WRITE_WINS"
    geo_regions: list = field(default_factory=lambda: ["us-east", "us-west", "eu-central"])
