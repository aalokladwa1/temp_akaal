"""
akaalEngine.discovery.models.snapshot
====================================
Canonical immutable discovery snapshot and fingerprint models.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.discovery.models.cdc import CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.environment import ConfigurationFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectInventory
from akaalEngine.discovery.models.partitioning import PartitionFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.statistics import StatisticsSnapshot
from akaalEngine.discovery.models.structure import ObjectStructureFacts
from akaalEngine.discovery.models.topology import TopologySnapshot
from akaalEngine.discovery.models.volume import VolumeSnapshot


class DiscoveryCompleteness(str, Enum):
    """Integrity and completeness level of the discovery snapshot."""
    FULL = "FULL"            # All requested namespaces, tables, and objects were successfully introspected
    PARTIAL = "PARTIAL"      # Some objects/schemas were skipped or failed due to permissions or errors
    DEGRADED = "DEGRADED"    # Essential catalogs failed; snapshot contains only minimal fallback facts
    FAILED = "FAILED"        # Discovery failed entirely


@dataclass(frozen=True)
class DiscoveryFingerprint:
    """Deterministic structural metadata fingerprint for drift detection."""
    sha256_hash: str
    component_hashes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.component_hashes, MappingProxyType):
            object.__setattr__(self, "component_hashes", MappingProxyType(dict(self.component_hashes)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha256_hash": self.sha256_hash,
            "component_hashes": dict(self.component_hashes),
        }


@dataclass(frozen=True)
class DiscoverySnapshot:
    """
    Canonical, versioned, deeply immutable root Discovery Snapshot.
    The single point-in-time authoritative physical facts document consumed by downstream authorities.
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completeness: DiscoveryCompleteness = DiscoveryCompleteness.FULL
    engine_identity: Optional[DiscoveredEndpointIdentity] = None
    namespaces: Optional[NamespaceInventory] = None
    objects: Optional[ObjectInventory] = None
    structures: Mapping[str, ObjectStructureFacts] = field(default_factory=lambda: MappingProxyType({}))
    programmables: Optional[ProgrammableInventory] = None
    partitioning: Mapping[str, PartitionFacts] = field(default_factory=lambda: MappingProxyType({}))
    statistics: Optional[StatisticsSnapshot] = None
    volume: Optional[VolumeSnapshot] = None
    permissions: Optional[PermissionAssessment] = None
    topology: Optional[TopologySnapshot] = None
    cdc: Optional[CDCPrerequisiteSnapshot] = None
    environment: Optional[ConfigurationFacts] = None
    sampled_data: Mapping[str, SampledRecordSet] = field(default_factory=lambda: MappingProxyType({}))
    fingerprint: Optional[DiscoveryFingerprint] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    errors: Tuple[str, ...] = field(default_factory=tuple)
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.structures, MappingProxyType):
            object.__setattr__(self, "structures", MappingProxyType(dict(self.structures)))
        if not isinstance(self.partitioning, MappingProxyType):
            object.__setattr__(self, "partitioning", MappingProxyType(dict(self.partitioning)))
        if not isinstance(self.sampled_data, MappingProxyType):
            object.__setattr__(self, "sampled_data", MappingProxyType(dict(self.sampled_data)))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))
        if not isinstance(self.errors, tuple):
            object.__setattr__(self, "errors", tuple(self.errors))

    def compute_sha256_fingerprint(self) -> DiscoveryFingerprint:
        """Computes a deterministic canonical structural hash over all material discovered physical facts."""
        component_hashes: dict[str, str] = {}
        
        # 1. Namespaces component
        ns_dict = self.namespaces.to_dict() if self.namespaces else {}
        ns_raw = json.dumps(ns_dict, sort_keys=True)
        component_hashes["namespaces"] = hashlib.sha256(ns_raw.encode("utf-8")).hexdigest()

        # 2. Objects component (tables and views)
        obj_dict = self.objects.to_dict() if self.objects else {}
        obj_raw = json.dumps(obj_dict, sort_keys=True)
        component_hashes["objects"] = hashlib.sha256(obj_raw.encode("utf-8")).hexdigest()

        # 3. Structures component (columns, PKs, FKs, constraints, indexes)
        struct_dict = {k: v.to_dict() for k, v in sorted(self.structures.items())}
        struct_raw = json.dumps(struct_dict, sort_keys=True)
        component_hashes["structures"] = hashlib.sha256(struct_raw.encode("utf-8")).hexdigest()

        # 4. Programmables component (routines, triggers, sequences, udts)
        prog_dict = self.programmables.to_dict() if self.programmables else {}
        prog_raw = json.dumps(prog_dict, sort_keys=True)
        component_hashes["programmables"] = hashlib.sha256(prog_raw.encode("utf-8")).hexdigest()

        # 5. Partitioning component
        part_dict = {k: v.to_dict() for k, v in sorted(self.partitioning.items())}
        part_raw = json.dumps(part_dict, sort_keys=True)
        component_hashes["partitioning"] = hashlib.sha256(part_raw.encode("utf-8")).hexdigest()

        # 6. Topology component
        topo_dict = self.topology.to_dict() if self.topology else {}
        topo_raw = json.dumps(topo_dict, sort_keys=True)
        component_hashes["topology"] = hashlib.sha256(topo_raw.encode("utf-8")).hexdigest()

        # 7. CDC prerequisites component
        cdc_dict = self.cdc.to_dict() if self.cdc else {}
        cdc_raw = json.dumps(cdc_dict, sort_keys=True)
        component_hashes["cdc"] = hashlib.sha256(cdc_raw.encode("utf-8")).hexdigest()

        # 8. Environment component
        env_dict = self.environment.to_dict() if self.environment else {}
        env_raw = json.dumps(env_dict, sort_keys=True)
        component_hashes["environment"] = hashlib.sha256(env_raw.encode("utf-8")).hexdigest()

        # Overall composite hash
        overall_raw = json.dumps(component_hashes, sort_keys=True)
        overall_hash = hashlib.sha256(overall_raw.encode("utf-8")).hexdigest()

        return DiscoveryFingerprint(sha256_hash=overall_hash, component_hashes=component_hashes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp_utc": self.timestamp_utc,
            "completeness": self.completeness.value,
            "engine_identity": self.engine_identity.to_dict() if self.engine_identity else None,
            "namespaces": self.namespaces.to_dict() if self.namespaces else None,
            "objects": self.objects.to_dict() if self.objects else None,
            "structures": {k: v.to_dict() for k, v in self.structures.items()},
            "programmables": self.programmables.to_dict() if self.programmables else None,
            "partitioning": {k: v.to_dict() for k, v in self.partitioning.items()},
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "volume": self.volume.to_dict() if self.volume else None,
            "permissions": self.permissions.to_dict() if self.permissions else None,
            "topology": self.topology.to_dict() if self.topology else None,
            "cdc": self.cdc.to_dict() if self.cdc else None,
            "environment": self.environment.to_dict() if self.environment else None,
            "sampled_data": {k: v.to_dict() for k, v in self.sampled_data.items()},
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "duration_ms": self.duration_ms,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
