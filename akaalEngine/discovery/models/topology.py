"""
akaalEngine.discovery.models.topology
====================================
Cluster topology, node roles, replication lag, and high availability fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class NodeRole(str, Enum):
    """Operational role of a cluster node."""
    PRIMARY = "PRIMARY"
    REPLICA = "REPLICA"
    STANDBY = "STANDBY"
    BROKER = "BROKER"
    COORDINATOR = "COORDINATOR"
    WORKER = "WORKER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClusterNodeFacts:
    """Discovered physical cluster node facts."""
    node_id: str
    host: str
    port: int
    role: NodeRole = NodeRole.PRIMARY
    is_active: bool = True
    replication_lag_ms: Optional[int] = None
    datacenter: Optional[str] = None
    rack: Optional[str] = None
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "role": self.role.value,
            "is_active": self.is_active,
            "replication_lag_ms": self.replication_lag_ms,
            "datacenter": self.datacenter,
            "rack": self.rack,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class TopologySnapshot:
    """Complete cluster and replication topology snapshot."""
    is_clustered: bool = False
    cluster_name: Optional[str] = None
    connected_node_role: NodeRole = NodeRole.PRIMARY
    nodes: Tuple[ClusterNodeFacts, ...] = field(default_factory=tuple)
    max_replication_lag_ms: Optional[int] = None
    rac_instances: Tuple[str, ...] = field(default_factory=tuple)
    availability_groups: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, tuple):
            object.__setattr__(self, "nodes", tuple(self.nodes))
        if not isinstance(self.rac_instances, tuple):
            object.__setattr__(self, "rac_instances", tuple(self.rac_instances))
        if not isinstance(self.availability_groups, tuple):
            object.__setattr__(self, "availability_groups", tuple(self.availability_groups))

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_clustered": self.is_clustered,
            "cluster_name": self.cluster_name,
            "connected_node_role": self.connected_node_role.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "max_replication_lag_ms": self.max_replication_lag_ms,
            "rac_instances": list(self.rac_instances),
            "availability_groups": list(self.availability_groups),
        }
