"""Healing configuration and profile definitions."""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class HealingProfile(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    SAFE_STAGED = "SAFE_STAGED"
    STRICT_FINANCE = "STRICT_FINANCE"
    STRICT_HEALTHCARE = "STRICT_HEALTHCARE"
    CUSTOM = "CUSTOM"


class ApprovalMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    SINGLE = "SINGLE"
    DUAL = "DUAL"
    DEPARTMENT = "DEPARTMENT"
    EXECUTIVE = "EXECUTIVE"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"


@dataclass
class SLAConfig:
    """SLA repair time constraints."""

    max_repair_duration_seconds: int = 300
    target_mttr_seconds: int = 60
    maintenance_window_start: Optional[str] = None


@dataclass
class HealingConfig:
    """Configuration options for the self-healing platform."""

    profile: HealingProfile = HealingProfile.AUTOMATIC
    approval_mode: ApprovalMode = ApprovalMode.AUTOMATIC
    enable_dry_run: bool = False
    enable_auto_verification: bool = True
    enable_sandbox_simulation: bool = True
    enable_multi_source_recovery: bool = True
    enable_conflict_resolution: bool = True
    enable_pattern_learning: bool = True
    max_parallel_workers: int = 4
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    sla_config: SLAConfig = field(default_factory=SLAConfig)
    custom_rules: Dict[str, Any] = field(default_factory=dict)
