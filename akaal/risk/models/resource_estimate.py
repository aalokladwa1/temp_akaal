"""
Akaal — Multi-Level Resource Estimation Model
=============================================
Calculates Min, Recommended, Peak, and Burst requirements for CPU, RAM, Disk, Network, and Workers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ResourceLevelEstimate:
    minimum: float
    recommended: float
    peak: float
    burst: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "minimum": round(self.minimum, 2),
            "recommended": round(self.recommended, 2),
            "peak": round(self.peak, 2),
            "burst": round(self.burst, 2),
        }


@dataclass
class ResourceEstimate:
    cpu_cores: ResourceLevelEstimate = field(default_factory=lambda: ResourceLevelEstimate(2, 4, 8, 16))
    memory_gb: ResourceLevelEstimate = field(default_factory=lambda: ResourceLevelEstimate(4, 8, 16, 32))
    disk_gb: ResourceLevelEstimate = field(default_factory=lambda: ResourceLevelEstimate(10, 50, 100, 200))
    network_mbps: ResourceLevelEstimate = field(default_factory=lambda: ResourceLevelEstimate(100, 500, 1000, 2000))
    workers: ResourceLevelEstimate = field(default_factory=lambda: ResourceLevelEstimate(2, 4, 8, 16))
    temp_storage_gb: float = 20.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores.to_dict(),
            "memory_gb": self.memory_gb.to_dict(),
            "disk_gb": self.disk_gb.to_dict(),
            "network_mbps": self.network_mbps.to_dict(),
            "workers": self.workers.to_dict(),
            "temp_storage_gb": round(self.temp_storage_gb, 2),
        }
