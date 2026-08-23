"""
akaalEngine.extensions.resolution.cache
======================================
Generation-aware strategy resolution cache.
Delivers O(1) performance for repeated strategy lookups while guaranteeing instantaneous invalidation on registry generation updates.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Sequence, Tuple

from akaalEngine.extensions.models.identity import AuthorityId, ProviderId, RegistryGeneration, StrategyId
from akaalEngine.extensions.models.strategy import StrategyContribution


class ResolutionCache:
    """
    Thread-safe, generation-keyed cache of resolved StrategyContribution lookups.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cached_generation: Optional[RegistryGeneration] = None
        self._entries: Dict[Tuple[Any, ...], StrategyContribution] = {}

    def get(
        self,
        generation: RegistryGeneration,
        provider_id: ProviderId,
        authority_id: AuthorityId,
        strategy_id: Optional[StrategyId] = None,
        contract_version: Optional[str] = None,
        required_capabilities: Optional[Sequence[str]] = None,
    ) -> Optional[StrategyContribution]:
        with self._lock:
            if self._cached_generation != generation:
                # Generation mismatch -> invalid cache
                self._entries.clear()
                self._cached_generation = generation
                return None

            caps_key = tuple(sorted(required_capabilities)) if required_capabilities else ()
            cache_key = (
                provider_id.value,
                authority_id.value,
                strategy_id.value if strategy_id else None,
                contract_version,
                caps_key,
            )
            return self._entries.get(cache_key)

    def put(
        self,
        generation: RegistryGeneration,
        provider_id: ProviderId,
        authority_id: AuthorityId,
        strategy: StrategyContribution,
        strategy_id: Optional[StrategyId] = None,
        contract_version: Optional[str] = None,
        required_capabilities: Optional[Sequence[str]] = None,
    ) -> None:
        with self._lock:
            if self._cached_generation != generation:
                self._entries.clear()
                self._cached_generation = generation

            caps_key = tuple(sorted(required_capabilities)) if required_capabilities else ()
            cache_key = (
                provider_id.value,
                authority_id.value,
                strategy_id.value if strategy_id else None,
                contract_version,
                caps_key,
            )
            self._entries[cache_key] = strategy

    def invalidate(self) -> None:
        with self._lock:
            self._entries.clear()
            self._cached_generation = None


default_resolution_cache = ResolutionCache()
