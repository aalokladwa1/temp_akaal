"""
Akaal — Discovery Context Model
===============================
Mutable runtime context passed through the discovery pipeline execution.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_policy import DiscoveryPolicy
from akaal.scout.models.capability_inventory import CapabilityInventory
from akaal.scout.models.schema_inventory import SchemaInventory
from akaal.scout.models.object_inventory import ObjectInventory
from akaal.scout.models.storage_inventory import StorageInventory
from akaal.scout.models.discovery_audit import DiscoveryAudit
from akaal.scout.models.cost_estimate import DiscoveryCostEstimate
from akaal.scout.models.permission_assessment import PermissionAssessment
from akaal.scout.models.discovery_health import DiscoveryHealth
from akaal.scout.models.discovery_manifest import DiscoveryManifest
from akaal.scout.models.discovery_report import (
    StageDiagnostics,
    EngineInfo,
    InstanceInfo,
    ClusterInfo,
    DiscoveryFingerprint,
)

if TYPE_CHECKING:
    from akaal.adapters.providers.base_provider import BaseDiscoveryProvider
    from akaal.scout.events.discovery_events import DiscoveryEventBus
    from akaal.scout.metrics.scout_metrics import ScoutMetrics


@dataclass
class DiscoveryContext:
    """
    Runtime context holding execution state throughout stage execution.
    Passed to pipeline stages.
    """
    request: DiscoveryRequest
    provider: Optional["BaseDiscoveryProvider"] = None
    event_bus: Optional["DiscoveryEventBus"] = None
    metrics: Optional["ScoutMetrics"] = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("akaal.scout"))

    discovery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = 0.0
    end_time: float = 0.0

    policy: DiscoveryPolicy = field(default_factory=DiscoveryPolicy)
    engine_info: EngineInfo = field(default_factory=lambda: EngineInfo("GENERIC", "Generic", "Generic"))
    version_info: Dict[str, Any] = field(default_factory=dict)
    instance_info: InstanceInfo = field(default_factory=lambda: InstanceInfo("localhost", 0, "default", "1.0"))
    cluster_info: ClusterInfo = field(default_factory=ClusterInfo)

    capability_inventory: CapabilityInventory = field(default_factory=CapabilityInventory)
    schema_inventory: SchemaInventory = field(default_factory=SchemaInventory)
    object_inventory: ObjectInventory = field(default_factory=ObjectInventory)
    storage_inventory: StorageInventory = field(default_factory=StorageInventory)

    permission_assessment: PermissionAssessment = field(default_factory=PermissionAssessment)
    health: DiscoveryHealth = field(default_factory=DiscoveryHealth)
    cost_estimate: DiscoveryCostEstimate = field(default_factory=DiscoveryCostEstimate)
    audit: Optional[DiscoveryAudit] = None
    manifest: Optional[DiscoveryManifest] = None

    fingerprint: Optional[DiscoveryFingerprint] = None
    stage_diagnostics: List[StageDiagnostics] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    read_only_verified: bool = False

    metadata_query_count: int = 0
    metadata_query_total_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.request:
            self.policy = self.request.get_effective_policy()

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        self.logger.warning("[ScoutContext Warning] %s", msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.logger.error("[ScoutContext Error] %s", msg)
