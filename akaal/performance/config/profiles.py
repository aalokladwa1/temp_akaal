"""
Performance Profiles and Feature Flags Configuration.
"""

from typing import Dict, Any
from enum import Enum


class FeatureFlag(str, Enum):
    ON = "ON"
    OFF = "OFF"
    AUTO = "AUTO"


class ProfileType(str, Enum):
    BALANCED = "Balanced"
    MAX_THROUGHPUT = "MaximumThroughput"
    LOW_MEMORY = "LowMemory"
    WAN_OPTIMIZED = "WanOptimized"
    SSD_OPTIMIZED = "SsdOptimized"


class PerformanceProfile:
    """Pre-defined config settings for optimizers and limits."""

    def __init__(
        self,
        name: ProfileType,
        version: str,
        feature_flags: Dict[str, FeatureFlag] = None,
        limits: Dict[str, Any] = None,
        thresholds: Dict[str, Any] = None
    ) -> None:
        self.name = name
        self.version = version
        self.feature_flags = feature_flags or {}
        self.limits = limits or {}
        self.thresholds = thresholds or {}


class PerformanceProfiles:
    """Central registry of predefined optimization profiles."""

    @staticmethod
    def get_profile(profile_type: ProfileType) -> PerformanceProfile:
        if profile_type == ProfileType.BALANCED:
            return PerformanceProfile(
                name=ProfileType.BALANCED,
                version="1.0",
                feature_flags={
                    "batch": FeatureFlag.AUTO,
                    "parallel": FeatureFlag.AUTO,
                    "compression": FeatureFlag.AUTO,
                    "vector": FeatureFlag.ON,
                    "memory": FeatureFlag.ON,
                },
                limits={"cpu_percent": 80.0, "ram_bytes": 1024 * 1024 * 1024 * 4},
                thresholds={"latency_ms": 30.0, "queue_depth": 50.0}
            )
        elif profile_type == ProfileType.MAX_THROUGHPUT:
            return PerformanceProfile(
                name=ProfileType.MAX_THROUGHPUT,
                version="1.0",
                feature_flags={
                    "batch": FeatureFlag.ON,
                    "parallel": FeatureFlag.ON,
                    "compression": FeatureFlag.ON,
                    "vector": FeatureFlag.ON,
                    "memory": FeatureFlag.ON,
                },
                limits={"cpu_percent": 95.0, "ram_bytes": 1024 * 1024 * 1024 * 8},
                thresholds={"latency_ms": 100.0, "queue_depth": 500.0}
            )
        elif profile_type == ProfileType.LOW_MEMORY:
            return PerformanceProfile(
                name=ProfileType.LOW_MEMORY,
                version="1.0",
                feature_flags={
                    "batch": FeatureFlag.AUTO,
                    "parallel": FeatureFlag.OFF,
                    "compression": FeatureFlag.ON,
                    "vector": FeatureFlag.OFF,
                    "memory": FeatureFlag.ON,
                },
                limits={"cpu_percent": 60.0, "ram_bytes": 1024 * 1024 * 1024 * 1},
                thresholds={"latency_ms": 20.0, "queue_depth": 10.0}
            )
        elif profile_type == ProfileType.WAN_OPTIMIZED:
            return PerformanceProfile(
                name=ProfileType.WAN_OPTIMIZED,
                version="1.0",
                feature_flags={
                    "batch": FeatureFlag.AUTO,
                    "parallel": FeatureFlag.AUTO,
                    "compression": FeatureFlag.ON,
                    "vector": FeatureFlag.ON,
                    "memory": FeatureFlag.ON,
                },
                limits={"cpu_percent": 75.0, "ram_bytes": 1024 * 1024 * 1024 * 3},
                thresholds={"latency_ms": 150.0, "queue_depth": 100.0}
            )
        # Default back to Balanced if unknown/SSD
        return PerformanceProfile(
            name=ProfileType.SSD_OPTIMIZED,
            version="1.0",
            feature_flags={
                "batch": FeatureFlag.ON,
                "parallel": FeatureFlag.ON,
                "compression": FeatureFlag.OFF,
                "vector": FeatureFlag.ON,
                "memory": FeatureFlag.ON,
            },
            limits={"cpu_percent": 90.0, "ram_bytes": 1024 * 1024 * 1024 * 6},
            thresholds={"latency_ms": 10.0, "queue_depth": 200.0}
        )
