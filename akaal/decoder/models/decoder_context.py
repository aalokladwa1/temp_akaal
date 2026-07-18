"""
Akaal — Decoder Context
=======================
Canonical immutable execution context passed through the entire Decoder normalization pipeline.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet


class ValidationProfile(str, Enum):
    QUICK = "QUICK"
    STANDARD = "STANDARD"
    STRICT = "STRICT"
    COMPLIANCE = "COMPLIANCE"


@dataclass(frozen=True)
class DecoderContext:
    """
    Immutable execution context passed to every engine in Decoder pipeline.
    Engines consume context without mutating it.
    """
    discovery_report: DiscoveryReport
    migration_ruleset: MigrationRuleSet
    validation_profile: ValidationProfile = ValidationProfile.STANDARD
    capability_matrix: Dict[str, Any] = field(default_factory=dict)
    compatibility_matrix: Dict[str, Any] = field(default_factory=dict)
    version_info: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    configuration: Dict[str, Any] = field(default_factory=dict)
    simulation_mode: bool = False
    decoder_version: str = "1.0.0"
