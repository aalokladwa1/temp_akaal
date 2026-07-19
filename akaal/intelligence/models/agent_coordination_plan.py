"""
AKAAL Enterprise Intelligence Platform — Agent Coordination Plan Model
=======================================================================
Represents regional worker allocation topologies and agent placement plans.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class AgentCoordinationPlan:
    """
    Immutable representation of strategic agent worker coordination topology.
    """

    plan_id: str
    total_recommended_agents: int
    primary_region: str
    secondary_regions: Tuple[str, ...] = field(default_factory=tuple)
    worker_distribution: Mapping[str, int] = field(default_factory=dict)
    failover_nodes: Tuple[str, ...] = field(default_factory=tuple)
    coordination_notes: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.secondary_regions, tuple):
            object.__setattr__(self, "secondary_regions", tuple(self.secondary_regions))
        if not isinstance(self.failover_nodes, tuple):
            object.__setattr__(self, "failover_nodes", tuple(self.failover_nodes))
        if not isinstance(self.coordination_notes, tuple):
            object.__setattr__(self, "coordination_notes", tuple(self.coordination_notes))

        if not isinstance(self.worker_distribution, MappingProxyType):
            object.__setattr__(
                self,
                "worker_distribution",
                MappingProxyType(dict(self.worker_distribution) if self.worker_distribution else {}),
            )
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "plan_id": self.plan_id,
            "total_recommended_agents": int(self.total_recommended_agents),
            "primary_region": self.primary_region,
            "secondary_regions": list(self.secondary_regions),
            "worker_distribution": dict(self.worker_distribution),
            "failover_nodes": list(self.failover_nodes),
            "coordination_notes": list(self.coordination_notes),
            "metadata": dict(self.metadata),
        }
