"""
akaalEngine.extensions.resolution.resolver
==========================================
Coordinates strategy resolution across the catalog, lifecycle manager, dependency inspector, and lease tracker.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.catalog.registry import ExtensionRegistry, default_extension_registry
from akaalEngine.extensions.dependencies.inspector import DependencyInspector, default_dependency_inspector
from akaalEngine.extensions.errors.taxonomy import (
    DependencyResolutionError,
    ExtensionNotFoundError,
    LifecycleTransitionError,
    ProviderNotFoundError,
    StrategyNotFoundError,
)
from akaalEngine.extensions.lifecycle.leases import HandleLeaseTracker, default_lease_tracker
from akaalEngine.extensions.lifecycle.manager import LifecycleManager, default_lifecycle_manager
from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId, StrategyId
from akaalEngine.extensions.resolution.cache import ResolutionCache, default_resolution_cache
from akaalEngine.extensions.resolution.handles import ResolvedStrategyHandle
from akaalEngine.extensions.resolution.selection import StrategySelector
from akaalEngine.extensions.truth.capability_resolver import CapabilityTruthResolver


class StrategyResolver:
    """
    Resolves executable strategy handles deterministically.
    """

    def __init__(
        self,
        registry: Optional[ExtensionRegistry] = None,
        lifecycle_manager: Optional[LifecycleManager] = None,
        lease_tracker: Optional[HandleLeaseTracker] = None,
        cache: Optional[ResolutionCache] = None,
        dep_inspector: Optional[DependencyInspector] = None,
    ) -> None:
        self._registry = registry or default_extension_registry
        self._lifecycle_mgr = lifecycle_manager or default_lifecycle_manager
        self._lease_tracker = lease_tracker or default_lease_tracker
        self._cache = cache if cache is not None else ResolutionCache()
        self._dep_inspector = dep_inspector or default_dependency_inspector

    def resolve_strategy(
        self,
        provider_id: ProviderId | str,
        authority_id: AuthorityId | str,
        strategy_id: Optional[StrategyId | str] = None,
        required_contract_version: Optional[str] = None,
        required_capabilities: Optional[Sequence[str]] = None,
    ) -> ResolvedStrategyHandle:
        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        auth_id = authority_id if isinstance(authority_id, AuthorityId) else AuthorityId(authority_id)
        strat_id = (strategy_id if isinstance(strategy_id, StrategyId) else StrategyId(strategy_id)) if strategy_id else None

        snapshot = self._registry.get_snapshot()
        generation = snapshot.generation

        # Check provider existence
        provider = snapshot.get_provider(prov_id)
        if provider is None:
            raise ProviderNotFoundError(f"Provider '{prov_id}' is not registered in registry generation {generation}.")

        # Check owning extension lifecycle
        owning_ext_id = snapshot.get_provider_owner(prov_id)
        if owning_ext_id is None:
            raise ExtensionNotFoundError(f"No owning extension found for provider '{prov_id}'.")

        ext_state = self._lifecycle_mgr.get_state(owning_ext_id)
        if ext_state != ExtensionLifecycleState.ACTIVE:
            raise LifecycleTransitionError(
                f"Cannot resolve strategy for provider '{prov_id}': owning extension '{owning_ext_id}' is in state '{ext_state.value}', not 'ACTIVE'."
            )

        # Fast path: Check generation cache
        selected_strategy = self._cache.get(
            generation=generation,
            provider_id=prov_id,
            authority_id=auth_id,
            strategy_id=strat_id,
            contract_version=required_contract_version,
            required_capabilities=required_capabilities,
        )

        if selected_strategy is None:
            candidates = snapshot.get_strategies_for_provider_and_authority(prov_id, auth_id)
            selected_strategy = StrategySelector.select(
                candidates=candidates,
                target_provider=prov_id.value,
                target_authority=auth_id.value,
                specific_strategy_id=strat_id.value if strat_id else None,
                required_contract_version=required_contract_version,
                required_capabilities=required_capabilities,
            )
            # Store in cache
            self._cache.put(
                generation=generation,
                provider_id=prov_id,
                authority_id=auth_id,
                strategy=selected_strategy,
                strategy_id=strat_id,
                contract_version=required_contract_version,
                required_capabilities=required_capabilities,
            )

        # Check strategy dependencies
        all_deps = list(provider.shared_dependencies) + list(selected_strategy.dependencies)
        dep_report = self._dep_inspector.inspect_all(selected_strategy.strategy_id.value, all_deps)
        if not dep_report.is_all_mandatory_satisfied:
            missing_names = [d.dependency_name for d in dep_report.missing_mandatory]
            raise DependencyResolutionError(
                f"Cannot resolve strategy '{selected_strategy.strategy_id}': missing mandatory dependencies: {missing_names}."
            )

        # Resolve effective capabilities
        resolved_caps = {}
        for cap_decl in list(provider.capabilities) + list(selected_strategy.capabilities):
            truth = CapabilityTruthResolver.resolve_capability_truth(
                declaration=cap_decl,
                capability_name=cap_decl.capability_name,
                lifecycle_state=ext_state,
                dep_report=dep_report,
                proof_references=selected_strategy.proof_references,
            )
            resolved_caps[cap_decl.capability_name] = truth

        # Instantiate strategy instance
        try:
            inst = selected_strategy.strategy_factory() if callable(selected_strategy.strategy_factory) else selected_strategy.strategy_factory
        except Exception as exc:
            raise StrategyNotFoundError(
                f"Failed to instantiate strategy '{selected_strategy.strategy_id}' via factory: {exc}"
            ) from exc

        # Acquire active lease
        lease_token = self._lease_tracker.acquire_lease(
            extension_id=owning_ext_id,
            strategy_id=selected_strategy.strategy_id,
        )

        return ResolvedStrategyHandle(
            extension_id=owning_ext_id,
            provider_id=prov_id,
            authority_id=auth_id,
            strategy_id=selected_strategy.strategy_id,
            implementation_version=selected_strategy.implementation_version,
            generation=generation,
            strategy_instance=inst,
            lease_token=lease_token,
            capabilities=resolved_caps,
            _lease_tracker=self._lease_tracker,
        )


default_strategy_resolver = StrategyResolver()
