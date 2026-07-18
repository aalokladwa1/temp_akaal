"""
Akaal — Discovery Cost Estimate Model
======================================
Pre-execution estimation vs post-execution actual resource consumption.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DiscoveryCostEstimate:
    """Pre-execution discovery resource estimation vs actual."""
    estimated_metadata_queries: int = 50
    expected_runtime_sec: float = 5.0
    estimated_memory_mb: float = 32.0
    estimated_network_kb: float = 128.0
    expected_objects_scanned: int = 100

    actual_metadata_queries: int = 0
    actual_runtime_sec: float = 0.0
    actual_objects_scanned: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimate": {
                "metadata_queries": self.estimated_metadata_queries,
                "expected_runtime_sec": self.expected_runtime_sec,
                "estimated_memory_mb": self.estimated_memory_mb,
                "estimated_network_kb": self.estimated_network_kb,
                "expected_objects_scanned": self.expected_objects_scanned,
            },
            "actual": {
                "metadata_queries": self.actual_metadata_queries,
                "actual_runtime_sec": self.actual_runtime_sec,
                "actual_objects_scanned": self.actual_objects_scanned,
            },
        }
