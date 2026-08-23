"""
tests.unit.engine_extensions.test_resolution_cache
==================================================
Tests for generation-aware resolution cache hits and automatic invalidation on registry generation bump.
"""

from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ProviderId,
    RegistryGeneration,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.resolution.cache import ResolutionCache


def test_resolution_cache_lifecycle_and_invalidation():
    cache = ResolutionCache()
    gen1 = RegistryGeneration(1)
    gen2 = RegistryGeneration(2)

    strat = StrategyContribution(
        strategy_id=StrategyId("strat-1"),
        authority_id=AuthorityId("connection"),
        provider_id=ProviderId("sqlite"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )

    prov_id = ProviderId("sqlite")
    auth_id = AuthorityId("connection")

    # Initial cache miss
    assert cache.get(gen1, prov_id, auth_id) is None

    # Populate cache
    cache.put(gen1, prov_id, auth_id, strat)
    assert cache.get(gen1, prov_id, auth_id) == strat

    # Querying with bumped generation 2 -> automatically invalidated
    assert cache.get(gen2, prov_id, auth_id) is None
    # Now querying generation 1 also misses because cache was cleared
    assert cache.get(gen1, prov_id, auth_id) is None
