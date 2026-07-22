"""
Cluster Discovery Service.
Automatically discovers active nodes, workers, platforms, capabilities, and health endpoints.
"""

from typing import Dict, Any, List
from threading import RLock
import time

from akaal.operations.digital_twin.model import DigitalTwinModel, ClusterNodeModel, WorkerModel
from akaal.operations.capability_registry.registry import OperationsCapabilityRegistry, PlatformCapability


class ClusterDiscoveryService:
    """Interrogates public platform facades and populates the Digital Twin."""

    def __init__(self, digital_twin: DigitalTwinModel, capability_registry: OperationsCapabilityRegistry) -> None:
        self._lock = RLock()
        self.digital_twin = digital_twin
        self.capability_registry = capability_registry
        self.last_discovery_time = 0.0

    def discover_all(self, distributed_runtime=None, streaming_runtime=None) -> Dict[str, Any]:
        """Queries active public facades to discover running workers and nodes."""
        with self._lock:
            # 1. Discover local default node
            node = ClusterNodeModel("node_primary", "127.0.0.1", total_cpu=16, total_memory_mb=65536)
            self.digital_twin.update_node(node)

            # 2. Discover workers if distributed_runtime facade is available
            if distributed_runtime and hasattr(distributed_runtime, "list_workers"):
                workers = distributed_runtime.list_workers()
                for w in workers:
                    wid = getattr(w, "worker_id", str(w))
                    self.digital_twin.update_worker(WorkerModel(wid, "node_primary"))

            # 3. Synchronize default capabilities into registry
            self.capability_registry.register_capability(PlatformCapability(
                platform_id="Platform1", version="1.0.0",
                supported_actions=["start_job", "pause_job", "resume_job", "cancel_job"]
            ))
            self.capability_registry.register_capability(PlatformCapability(
                platform_id="Platform2", version="1.0.0",
                supported_actions=["register_worker", "drain_worker", "restart_worker"]
            ))
            self.capability_registry.register_capability(PlatformCapability(
                platform_id="Platform3", version="1.0.0",
                supported_actions=["start_stream", "stop_stream", "watermark_status"]
            ))
            self.capability_registry.register_capability(PlatformCapability(
                platform_id="Platform5", version="1.0.0",
                supported_actions=["apply_ddl", "rollback_ddl", "version_graph"]
            ))
            self.capability_registry.register_capability(PlatformCapability(
                platform_id="Platform6", version="1.0.0",
                supported_actions=["set_profile", "trigger_optimization", "hot_reload"]
            ))

            self.last_discovery_time = time.time()
            return {
                "discovered_nodes": len(self.digital_twin.nodes),
                "discovered_workers": len(self.digital_twin.workers),
                "timestamp": self.last_discovery_time
            }
