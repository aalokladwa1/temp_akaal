"""
akaalEngine.extensions.resolution.resolver
==========================================
Coordinates strategy resolution across the catalog, lifecycle manager, dependency inspector, and lease tracker.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.catalog.registry import ExtensionRegistry, default_extension_registry
from akaalEngine.extensions.truth.authority_store import (
    CertificationAuthorityStore,
    default_certification_authority_store,
)
from akaalEngine.extensions.dependencies.inspector import DependencyInspector, default_dependency_inspector
from akaalEngine.extensions.errors.taxonomy import (
    CapabilityNotSupportedError,
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
from akaalEngine.extensions.models.sanitized import SanitizedStrategyDescriptor
from akaalEngine.extensions.resolution.cache import ResolutionCache, default_resolution_cache
from akaalEngine.extensions.resolution.handles import ResolvedStrategyHandle
from akaalEngine.extensions.resolution.selection import StrategySelector
from akaalEngine.extensions.truth.capability_resolver import CapabilityTruthResolver

_STANDARD_OPERATION_CAPABILITIES: dict[str, dict[str, Sequence[str]]] = {
    "discovery": {
        "DISCOVERY": ("SCHEMA_DISCOVERY",),
        "SCHEMA_DISCOVERY": ("SCHEMA_DISCOVERY",),
        "TABLE_DISCOVERY": ("TABLE_DISCOVERY",),
        "PARTITION_DISCOVERY": ("PARTITION_DISCOVERY",),
    },
    "cdc": {
        "CDC": ("CDC_STREAM",),
        "CDC_STREAM": ("CDC_STREAM",),
        "CDC_SNAPSHOT": ("CDC_SNAPSHOT",),
    },
    "transport": {
        "BULK_READ": ("BULK_READ",),
        "BULK_WRITE": ("BULK_WRITE",),
    },
    "validation": {
        "VALIDATION": ("ROW_HASH_VALIDATION",),
    },
}


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
        certification_authority_store: Optional[CertificationAuthorityStore] = None,
    ) -> None:
        self._registry = registry or default_extension_registry
        self._lifecycle_mgr = lifecycle_manager or default_lifecycle_manager
        self._lease_tracker = lease_tracker or default_lease_tracker
        self._cache = cache if cache is not None else ResolutionCache()
        self._dep_inspector = dep_inspector or default_dependency_inspector
        self._cert_store = certification_authority_store or default_certification_authority_store

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
        owning_manifest = snapshot.get_extension(owning_ext_id)
        owning_ext_version = owning_manifest.version if owning_manifest is not None else None
        resolved_caps = {}
        for cap_decl in list(provider.capabilities) + list(selected_strategy.capabilities):
            truth = CapabilityTruthResolver.resolve_capability_truth(
                declaration=cap_decl,
                capability_name=cap_decl.capability_name,
                lifecycle_state=ext_state,
                dep_report=dep_report,
                proof_references=selected_strategy.proof_references,
                certifications=selected_strategy.certifications,
                authority_store=self._cert_store,
                extension_id=owning_ext_id.value,
                extension_version=owning_ext_version,
                provider_id=prov_id.value,
                strategy_id=selected_strategy.strategy_id.value,
            )
            resolved_caps[cap_decl.capability_name] = truth

        # Capability enforcement: verify all required capabilities BEFORE factory instantiation
        if required_capabilities:
            for req_cap in required_capabilities:
                key = req_cap.strip().upper()
                cap_truth = resolved_caps.get(key)
                if cap_truth is None or not cap_truth.is_supported:
                    diagnostic = cap_truth.diagnostic if cap_truth is not None else "no capability declaration present"
                    raise CapabilityNotSupportedError(
                        f"Strategy '{selected_strategy.strategy_id}' (provider '{prov_id}', authority "
                        f"'{auth_id}') does not support required capability '{key}': {diagnostic}.",
                        details={
                            "provider_id": str(prov_id),
                            "authority_id": str(auth_id),
                            "strategy_id": str(selected_strategy.strategy_id),
                            "capability_name": key,
                        },
                    )

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

    def inspect_strategy(
        self,
        provider_id: ProviderId | str,
        authority_id: AuthorityId | str,
        strategy_id: Optional[StrategyId | str] = None,
        required_contract_version: Optional[str] = None,
    ) -> SanitizedStrategyDescriptor:
        """
        Inspects provider/strategy metadata and declared capabilities WITHOUT instantiating
        or exposing executable physical authority.
        """
        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        auth_id = authority_id if isinstance(authority_id, AuthorityId) else AuthorityId(authority_id)
        strat_id = (strategy_id if isinstance(strategy_id, StrategyId) else StrategyId(strategy_id)) if strategy_id else None

        snapshot = self._registry.get_snapshot()
        provider = snapshot.get_provider(prov_id)
        if provider is None:
            raise ProviderNotFoundError(f"Provider '{prov_id}' is not registered.")
        candidates = snapshot.get_strategies_for_provider_and_authority(prov_id, auth_id)
        selected_strategy = StrategySelector.select(
            candidates=candidates,
            target_provider=prov_id.value,
            target_authority=auth_id.value,
            specific_strategy_id=strat_id.value if strat_id else None,
            required_contract_version=required_contract_version,
        )
        return SanitizedStrategyDescriptor(
            strategy_id=selected_strategy.strategy_id.value,
            authority_id=selected_strategy.authority_id.value,
            provider_id=selected_strategy.provider_id.value,
            implementation_version=selected_strategy.implementation_version,
            contract_version_range=selected_strategy.contract_version_range.raw_expression,
            description=selected_strategy.description,
            capabilities=tuple(c.capability_name for c in selected_strategy.capabilities),
            configuration_schema=selected_strategy.configuration_schema.to_sanitized() if selected_strategy.configuration_schema else None,
        )

    def resolve_executable_strategy(
        self,
        provider_id: ProviderId | str,
        authority_id: AuthorityId | str,
        operation: str,
        strategy_id: Optional[StrategyId | str] = None,
        required_contract_version: Optional[str] = None,
        additional_required_capabilities: Optional[Sequence[str]] = None,
    ) -> ResolvedStrategyHandle:
        """
        Resolves an executable strategy handle.
        Security-critical: `operation` is strictly MANDATORY (no default None).
        The canonical authority maps `operation` to required capabilities and positively
        establishes them BEFORE physical strategy instantiation.
        """
        if not operation or not isinstance(operation, str) or not operation.strip():
            raise ValueError("Executable strategy resolution requires an explicit, non-empty operation.")

        auth_id_str = authority_id.value if isinstance(authority_id, AuthorityId) else str(authority_id)
        norm_op = operation.strip().upper()
        standard_caps = _STANDARD_OPERATION_CAPABILITIES.get(auth_id_str.lower(), {}).get(norm_op)
        if standard_caps:
            req_caps = list(standard_caps)
        else:
            req_caps = [norm_op]

        if additional_required_capabilities:
            req_caps.extend(additional_required_capabilities)

        return self.resolve_strategy(
            provider_id=provider_id,
            authority_id=authority_id,
            strategy_id=strategy_id,
            required_contract_version=required_contract_version,
            required_capabilities=req_caps,
        )


default_strategy_resolver = StrategyResolver()
