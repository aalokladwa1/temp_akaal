"""ReplicatorRegistry: Thread-safe registry for domain replicators."""

import threading
from typing import Dict, List, Optional
from akaal.replication.core.interfaces import IDomainReplicator


class ReplicatorRegistry:
    """Thread-safe registry managing domain replicators."""

    def __init__(self):
        self._domain_replicators: Dict[str, IDomainReplicator] = {}
        self._capability_map: Dict[str, IDomainReplicator] = {}
        self._lock = threading.RLock()

    def register_domain_replicator(self, replicator: IDomainReplicator) -> None:
        """Register a domain replicator."""
        with self._lock:
            self._domain_replicators[replicator.domain_name] = replicator
            for cap_id in replicator.capabilities:
                self._capability_map[cap_id] = replicator

    def get_domain_replicator(self, domain_name: str) -> Optional[IDomainReplicator]:
        """Retrieve domain replicator by name."""
        with self._lock:
            return self._domain_replicators.get(domain_name)

    def get_replicator_for_capability(self, capability_id: str) -> Optional[IDomainReplicator]:
        """Lookup domain replicator for a capability."""
        with self._lock:
            if capability_id in self._capability_map:
                return self._capability_map[capability_id]
            for cap_key, replicator in self._capability_map.items():
                if cap_key.startswith(capability_id) or capability_id.startswith(cap_key):
                    return replicator
            return None

    def list_domains(self) -> List[str]:
        """List registered domain names."""
        with self._lock:
            return list(self._domain_replicators.keys())

    def list_all_capabilities(self) -> List[str]:
        """List all capabilities supported."""
        with self._lock:
            return list(self._capability_map.keys())
