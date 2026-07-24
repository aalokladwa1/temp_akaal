"""ResilienceEngRegistry: Thread-safe registry for domain resilience modules."""

import threading
from typing import Dict, List, Optional
from akaal.resilience_eng.core.interfaces import IDomainResilienceModule


class ResilienceEngRegistry:
    """Thread-safe registry managing domain resilience modules."""

    def __init__(self):
        self._domain_modules: Dict[str, IDomainResilienceModule] = {}
        self._capability_map: Dict[str, IDomainResilienceModule] = {}
        self._lock = threading.RLock()

    def register_domain_module(self, module: IDomainResilienceModule) -> None:
        with self._lock:
            self._domain_modules[module.domain_name] = module
            for cap_id in module.capabilities:
                self._capability_map[cap_id] = module

    def get_domain_module(self, domain_name: str) -> Optional[IDomainResilienceModule]:
        with self._lock:
            return self._domain_modules.get(domain_name)

    def list_domains(self) -> List[str]:
        with self._lock:
            return list(self._domain_modules.keys())

    def list_all_capabilities(self) -> List[str]:
        with self._lock:
            return list(self._capability_map.keys())
