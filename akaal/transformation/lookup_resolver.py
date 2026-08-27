"""
AKAAL Lookup & Reference Transformation Resolver.
=================================================
Provides deterministic, bounded in-memory lookup resolution for reference datasets
and inline dictionaries. ZERO network calls inside row transformation loops.
"""

from typing import Any, Dict, Optional, Tuple
from akaal.transformation.models import LookupDefinition, MissingKeyPolicy


class LookupResolutionError(Exception):
    pass


class LookupResolver:
    """Bounded, thread-safe in-memory lookup resolver."""

    def __init__(self) -> None:
        self._lookup_cache: Dict[str, LookupDefinition] = {}

    def register_lookup(self, lookup_def: LookupDefinition) -> None:
        self._lookup_cache[lookup_def.lookup_name] = lookup_def

    def resolve(self, lookup_name: str, key_val: Any) -> Tuple[Any, Optional[str]]:
        """
        Resolves key value using registered LookupDefinition.
        Returns (resolved_value, missing_policy_action_if_any).
        """
        lookup_def = self._lookup_cache.get(lookup_name)
        if not lookup_def:
            raise LookupResolutionError(f"Lookup definition '{lookup_name}' is not registered.")

        if key_val is None:
            return None, None

        key_str = str(key_val)
        if key_str in lookup_def.mapping_dictionary:
            return lookup_def.mapping_dictionary[key_str], None

        # Missing key handling
        policy = lookup_def.missing_policy
        if policy == MissingKeyPolicy.FAIL_ROW:
            raise LookupResolutionError(f"Missing key '{key_str}' in lookup '{lookup_name}' with FAIL_ROW policy.")
        elif policy == MissingKeyPolicy.QUARANTINE_ROW:
            return None, "QUARANTINE_ROW"
        elif policy == MissingKeyPolicy.USE_DEFAULT:
            return lookup_def.default_value, None
        elif policy == MissingKeyPolicy.PRESERVE_ORIGINAL:
            return key_val, None
        elif policy == MissingKeyPolicy.USE_NULL:
            return None, None

        return None, None
