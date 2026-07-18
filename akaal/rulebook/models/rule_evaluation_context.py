"""
Akaal — Rule Evaluation Context
===============================
Canonical immutable context object passed through the entire Rulebook execution pipeline.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from akaal.scout.models.discovery_report import DiscoveryReport

if TYPE_CHECKING:
    from akaal.core.pipeline import MigrationConfig
    from akaal.scout.models.discovery_policy import DiscoveryPolicy


@dataclass(frozen=True)
class RuleEvaluationContext:
    """
    Immutable execution context passed to every engine in Rulebook pipeline.
    Engines consume context without mutating it.
    """
    discovery_report: DiscoveryReport
    target_engine: str = "POSTGRESQL"
    migration_config: Optional[Any] = None
    org_policies: Dict[str, Any] = field(default_factory=dict)
    discovery_policy: Optional[Any] = None
    capability_matrix: Dict[str, Any] = field(default_factory=dict)
    resolved_policy_chain: List[Dict[str, Any]] = field(default_factory=list)
    rule_registry_ref: Optional[Any] = None
    rule_pack_registry_ref: Optional[Any] = None
    simulation_mode: bool = False
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rulebook_version: str = "1.0.0"
