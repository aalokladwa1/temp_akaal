"""
AKAAL Enterprise Intelligence Platform — Migration Simulation Result Model
==========================================================================
Represents deterministic simulation projections for downtime bounds, resource curves,
and risk probability distributions.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class MigrationSimulationResult:
    """
    Immutable representation of deterministic migration simulation output.
    """

    simulation_id: str
    projected_downtime_seconds_min: float
    projected_downtime_seconds_max: float
    projected_downtime_seconds_p95: float
    projected_total_duration_seconds: float
    estimated_throughput_records_per_sec: float
    peak_memory_mb_estimate: float
    peak_cpu_cores_estimate: float
    failure_probability: float  # 0.0 to 1.0
    bottleneck_stages: Tuple[str, ...] = field(default_factory=tuple)
    simulated_risk_factors: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.bottleneck_stages, tuple):
            object.__setattr__(self, "bottleneck_stages", tuple(self.bottleneck_stages))
        if not isinstance(self.simulated_risk_factors, tuple):
            object.__setattr__(self, "simulated_risk_factors", tuple(self.simulated_risk_factors))

        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "simulation_id": self.simulation_id,
            "projected_downtime_seconds_min": float(self.projected_downtime_seconds_min),
            "projected_downtime_seconds_max": float(self.projected_downtime_seconds_max),
            "projected_downtime_seconds_p95": float(self.projected_downtime_seconds_p95),
            "projected_total_duration_seconds": float(self.projected_total_duration_seconds),
            "estimated_throughput_records_per_sec": float(self.estimated_throughput_records_per_sec),
            "peak_memory_mb_estimate": float(self.peak_memory_mb_estimate),
            "peak_cpu_cores_estimate": float(self.peak_cpu_cores_estimate),
            "failure_probability": float(self.failure_probability),
            "bottleneck_stages": list(self.bottleneck_stages),
            "simulated_risk_factors": list(self.simulated_risk_factors),
            "metadata": dict(self.metadata),
        }
