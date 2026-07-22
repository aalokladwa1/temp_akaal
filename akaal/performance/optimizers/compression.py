"""
Intelligent Compression Pipeline.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class AdaptiveCompressionPipeline(PluginOptimizer):
    """Dynamically switches compression algorithms (lz4, zstd, gzip, raw) based on network metrics."""

    def __init__(self) -> None:
        super().__init__("compression")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        current_codec = current_config.get("compression_codec", "raw")
        network_latency = metrics.get("network_latency_ms", 10.0)
        bandwidth_mbps = metrics.get("network_bandwidth_mbps", 100.0)

        new_codec = current_codec
        if network_latency > 100.0 and bandwidth_mbps < 10.0:
            # Low bandwidth, high latency => use high compression (zstd)
            new_codec = "zstd"
        elif network_latency > 50.0:
            # Medium latency => use fast lz4
            new_codec = "lz4"
        elif bandwidth_mbps > 500.0:
            # Super fast local network => raw transfers
            new_codec = "raw"

        if new_codec != current_codec:
            return {"compression_codec": new_codec}
        return None
