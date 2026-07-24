"""ReliabilityRegistry: Thread-safe registry for domain reliability modules."""

import threading
from typing import Dict, List, Optional
from akaal.reliability.core.interfaces import IDomainReliabilityModule


class ReliabilityRegistry:
    """Thread-safe registry managing domain reliability modules."""

    def __init__(self):
        self._domain_modules: Dict[str, IDomainReliabilityModule] = {}
        self._capability_map: Dict[str, IDomainReliabilityModule] = {}
        self._lock = threading.RLock()

    def register_domain_module(self, module: IDomainReliabilityModule) -> None:
        """Register a domain reliability module."""
        with self._lock:
            self._domain_modules[module.domain_name] = module
            for cap_id in module.capabilities:
                self._capability_map[cap_id] = module

    def get_domain_module(self, domain_name: str) -> Optional[IDomainReliabilityModule]:
        """Retrieve domain module by name."""
        with self._lock:
            return self._domain_modules.get(domain_name)

    def get_module_for_capability(self, capability_id: str) -> Optional[IDomainReliabilityModule]:
        """Lookup domain module for a capability."""
        with self._lock:
            if capability_id in self._capability_map:
                return self._capability_map[capability_id]
            for cap_key, module in self._capability_map.items():
                if cap_key.startswith(capability_id) or capability_id.startswith(cap_key):
                    return module
            return None

    def list_domains(self) -> List[str]:
        """List registered domain names."""
        with self._lock:
            return list(self._domain_modules.keys())

    def list_all_capabilities(self) -> List[str]:
        """List all capabilities supported."""
        with self._lock:
            return list(self._capability_map.keys())
