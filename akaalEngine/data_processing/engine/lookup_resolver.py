"""
akaalEngine.data_processing.engine.lookup_resolver
===================================================
Thread-safe LookupResolver managing lookup maps and missing key policies.
Mined from `akaal/transformation/lookup_resolver.py`.
"""

from threading import RLock
from typing import Any, Dict, Optional, Tuple

from akaalEngine.data_processing.models.plan import LookupDefinition


class LookupResolver:
    """Thread-safe reference lookup map resolver."""

    def __init__(self) -> None:
        self._lookups: Dict[str, LookupDefinition] = {}
        self._lock = RLock()

    def register_lookup(self, lookup_def: LookupDefinition) -> None:
        with self._lock:
            self._lookups[lookup_def.lookup_name] = lookup_def

    def resolve(self, lookup_name: str, key_val: Any) -> Tuple[Any, str]:
        """
        Resolves lookup key.
        Returns (resolved_value, policy_action).
        """
        with self._lock:
            lookup = self._lookups.get(lookup_name)
            if not lookup:
                return None, "QUARANTINE_RECORD"

            if key_val in lookup.mapping_data:
                return lookup.mapping_data[key_val], "SUCCESS"

            policy = lookup.missing_key_policy
            if policy == "USE_NULL":
                return None, "SUCCESS"
            elif policy == "USE_DEFAULT":
                return None, "SUCCESS"
            else:
                return None, "QUARANTINE_RECORD"
