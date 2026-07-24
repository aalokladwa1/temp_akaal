"""ValidatorRegistry: Thread-safe registry for domain validators and plugins."""

import threading
from typing import Dict, List, Optional
from akaal.validation.core.interfaces import IDomainValidator, IValidator


class ValidatorRegistry:
    """Thread-safe registry managing domain validators and plugins."""

    def __init__(self):
        self._domain_validators: Dict[str, IDomainValidator] = {}
        self._capability_map: Dict[str, IDomainValidator] = {}
        self._lock = threading.RLock()

    def register_domain_validator(self, validator: IDomainValidator) -> None:
        """Register a domain-driven validator."""
        with self._lock:
            self._domain_validators[validator.domain_name] = validator
            for cap_id in validator.capabilities:
                self._capability_map[cap_id] = validator

    def get_domain_validator(self, domain_name: str) -> Optional[IDomainValidator]:
        """Retrieve domain validator by domain name."""
        with self._lock:
            return self._domain_validators.get(domain_name)

    def get_validator_for_capability(self, capability_id: str) -> Optional[IDomainValidator]:
        """Lookup domain validator managing a specific capability (supports exact and prefix match)."""
        with self._lock:
            if capability_id in self._capability_map:
                return self._capability_map[capability_id]
            # Fallback prefix matching (e.g. 'Cap 1' matches 'Cap 1: Structural Validation')
            for cap_key, validator in self._capability_map.items():
                if cap_key.startswith(capability_id) or capability_id.startswith(cap_key):
                    return validator
            return None

    def list_domains(self) -> List[str]:
        """List registered domain names."""
        with self._lock:
            return list(self._domain_validators.keys())

    def list_all_capabilities(self) -> List[str]:
        """List all capabilities supported across all registered domain validators."""
        with self._lock:
            return list(self._capability_map.keys())
