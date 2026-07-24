"""HealerRegistry: Thread-safe registry for domain healers and plugins."""

import threading
from typing import Dict, List, Optional
from akaal.healing.core.interfaces import IDomainHealer, IHealer


class HealerRegistry:
    """Thread-safe registry managing domain healers."""

    def __init__(self):
        self._domain_healers: Dict[str, IDomainHealer] = {}
        self._capability_map: Dict[str, IDomainHealer] = {}
        self._lock = threading.RLock()

    def register_domain_healer(self, healer: IDomainHealer) -> None:
        """Register a domain healer."""
        with self._lock:
            self._domain_healers[healer.domain_name] = healer
            for cap_id in healer.capabilities:
                self._capability_map[cap_id] = healer

    def get_domain_healer(self, domain_name: str) -> Optional[IDomainHealer]:
        """Retrieve domain healer by name."""
        with self._lock:
            return self._domain_healers.get(domain_name)

    def get_healer_for_capability(self, capability_id: str) -> Optional[IDomainHealer]:
        """Lookup domain healer for a capability."""
        with self._lock:
            if capability_id in self._capability_map:
                return self._capability_map[capability_id]
            for cap_key, healer in self._capability_map.items():
                if cap_key.startswith(capability_id) or capability_id.startswith(cap_key):
                    return healer
            return None

    def list_domains(self) -> List[str]:
        """List registered domain names."""
        with self._lock:
            return list(self._domain_healers.keys())

    def list_all_capabilities(self) -> List[str]:
        """List all capabilities supported."""
        with self._lock:
            return list(self._capability_map.keys())
