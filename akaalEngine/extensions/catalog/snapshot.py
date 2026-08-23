"""
akaalEngine.extensions.catalog.snapshot
=======================================
Immutable, O(1)-indexed snapshot of all published extensions, providers, and authority strategies.
Lock-free read performance; never mutated in place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    RegistryGeneration,
    StrategyId,
)
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution


@dataclass(frozen=True)
class RegistrySnapshot:
    """
    Immutable snapshot of the entire Extensions Authority catalog at a specific generation.
    Supports O(1) multi-dimensional lookups by extension, provider, authority, strategy, and compound keys.
    """
    generation: RegistryGeneration
    extensions: Mapping[ExtensionId, ExtensionManifest] = field(default_factory=dict)
    providers: Mapping[ProviderId, ProviderContribution] = field(default_factory=dict)
    strategies: Mapping[StrategyId, StrategyContribution] = field(default_factory=dict)

    # Multi-dimensional indexes
    # provider_id -> tuple of strategy_ids
    _provider_strategies: Mapping[ProviderId, Sequence[StrategyId]] = field(default_factory=dict)
    # authority_id -> tuple of strategy_ids
    _authority_strategies: Mapping[AuthorityId, Sequence[StrategyId]] = field(default_factory=dict)
    # (provider_id, authority_id) -> tuple of strategy_ids
    _provider_authority_strategies: Mapping[Tuple[ProviderId, AuthorityId], Sequence[StrategyId]] = field(default_factory=dict)
    # provider_id -> owning extension_id
    _provider_owners: Mapping[ProviderId, ExtensionId] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        generation: RegistryGeneration,
        manifests: Sequence[ExtensionManifest],
    ) -> RegistrySnapshot:
        """Constructs an immutable snapshot and all lookup indexes from a list of manifests."""
        ext_map: Dict[ExtensionId, ExtensionManifest] = {}
        prov_map: Dict[ProviderId, ProviderContribution] = {}
        strat_map: Dict[StrategyId, StrategyContribution] = {}

        prov_strats: Dict[ProviderId, List[StrategyId]] = {}
        auth_strats: Dict[AuthorityId, List[StrategyId]] = {}
        prov_auth_strats: Dict[Tuple[ProviderId, AuthorityId], List[StrategyId]] = {}
        prov_owners: Dict[ProviderId, ExtensionId] = {}

        for manifest in manifests:
            ext_map[manifest.extension_id] = manifest
            for prov in manifest.provider_contributions:
                prov_map[prov.provider_id] = prov
                prov_owners[prov.provider_id] = manifest.extension_id

                # Clear old strategy index for this provider to prevent duplicate entries on replacement
                prov_strats[prov.provider_id] = []
                for auth_id in prov.get_all_authorities():
                    prov_auth_strats[(prov.provider_id, auth_id)] = []

                for strat in prov.strategies:
                    strat_map[strat.strategy_id] = strat
                    prov_strats[prov.provider_id].append(strat.strategy_id)

                    if strat.authority_id not in auth_strats:
                        auth_strats[strat.authority_id] = []
                    if strat.strategy_id not in auth_strats[strat.authority_id]:
                        auth_strats[strat.authority_id].append(strat.strategy_id)

                    pair_key = (prov.provider_id, strat.authority_id)
                    if pair_key not in prov_auth_strats:
                        prov_auth_strats[pair_key] = []
                    if strat.strategy_id not in prov_auth_strats[pair_key]:
                        prov_auth_strats[pair_key].append(strat.strategy_id)

        import types
        return cls(
            generation=generation,
            extensions=types.MappingProxyType(ext_map),
            providers=types.MappingProxyType(prov_map),
            strategies=types.MappingProxyType(strat_map),
            _provider_strategies=types.MappingProxyType({k: tuple(v) for k, v in prov_strats.items()}),
            _authority_strategies=types.MappingProxyType({k: tuple(v) for k, v in auth_strats.items()}),
            _provider_authority_strategies=types.MappingProxyType({k: tuple(v) for k, v in prov_auth_strats.items()}),
            _provider_owners=types.MappingProxyType(prov_owners),
        )

    def get_extension(self, extension_id: ExtensionId) -> Optional[ExtensionManifest]:
        return self.extensions.get(extension_id)

    def get_provider(self, provider_id: ProviderId) -> Optional[ProviderContribution]:
        return self.providers.get(provider_id)

    def get_strategy(self, strategy_id: StrategyId) -> Optional[StrategyContribution]:
        return self.strategies.get(strategy_id)

    def get_strategies_for_provider(self, provider_id: ProviderId) -> Sequence[StrategyContribution]:
        strat_ids = self._provider_strategies.get(provider_id, ())
        return tuple(self.strategies[sid] for sid in strat_ids if sid in self.strategies)

    def get_strategies_for_authority(self, authority_id: AuthorityId) -> Sequence[StrategyContribution]:
        strat_ids = self._authority_strategies.get(authority_id, ())
        return tuple(self.strategies[sid] for sid in strat_ids if sid in self.strategies)

    def get_strategies_for_provider_and_authority(
        self,
        provider_id: ProviderId,
        authority_id: AuthorityId,
    ) -> Sequence[StrategyContribution]:
        strat_ids = self._provider_authority_strategies.get((provider_id, authority_id), ())
        return tuple(self.strategies[sid] for sid in strat_ids if sid in self.strategies)

    def get_provider_owner(self, provider_id: ProviderId) -> Optional[ExtensionId]:
        return self._provider_owners.get(provider_id)

    def list_all_extensions(self) -> Sequence[ExtensionManifest]:
        return tuple(self.extensions.values())

    def list_all_providers(self) -> Sequence[ProviderContribution]:
        return tuple(self.providers.values())
