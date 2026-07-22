"""
Operations Capability Registry.
Discovers and registers advertised operational capabilities across platforms via public contracts.
"""

from typing import Dict, Any, List, Optional
from threading import RLock
import time


class PlatformCapability:
    """Advertised capabilities metadata of a target platform."""

    def __init__(
        self,
        platform_id: str,
        version: str,
        supported_actions: List[str],
        health_capable: bool = True,
        metrics_exposed: List[str] = None,
        maintenance_capable: bool = True,
        diagnostic_capable: bool = True,
        feature_flags: Optional[Dict[str, bool]] = None
    ) -> None:
        self.platform_id = platform_id
        self.version = version
        self.supported_actions = supported_actions
        self.health_capable = health_capable
        self.metrics_exposed = metrics_exposed or []
        self.maintenance_capable = maintenance_capable
        self.diagnostic_capable = diagnostic_capable
        self.feature_flags = feature_flags or {}
        self.registered_at = time.time()
        self.last_refreshed = time.time()


class OperationsCapabilityRegistry:
    """Central descriptive registry for all platform operational capabilities."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._capabilities: Dict[str, PlatformCapability] = {}

    def register_capability(self, capability: PlatformCapability) -> None:
        with self._lock:
            capability.last_refreshed = time.time()
            self._capabilities[capability.platform_id] = capability

    def get_capability(self, platform_id: str) -> Optional[PlatformCapability]:
        with self._lock:
            return self._capabilities.get(platform_id)

    def list_capabilities(self) -> Dict[str, PlatformCapability]:
        with self._lock:
            return dict(self._capabilities)

    def supports_action(self, platform_id: str, action: str) -> bool:
        with self._lock:
            cap = self._capabilities.get(platform_id)
            if not cap:
                return False
            return action.lower() in [act.lower() for act in cap.supported_actions]
