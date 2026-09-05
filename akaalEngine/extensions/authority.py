"""
akaalEngine.extensions.authority
================================
Authority #2: Canonical Extensions Authority Façade.
The single cross-authority provider-extension foundation for the reconstructed AKAAL Engine.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Mapping, Optional, Sequence

from akaalEngine.extensions.catalog.registry import ExtensionRegistry, default_extension_registry
from akaalEngine.extensions.catalog.snapshot import RegistrySnapshot
from akaalEngine.extensions.configuration.sanitizer import ConfigurationSanitizer
from akaalEngine.extensions.configuration.validator import ConfigurationValidator
from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.dependencies.inspector import DependencyInspector, default_dependency_inspector
from akaalEngine.extensions.errors.taxonomy import (
    ExtensionHandleLeakError,
    ExtensionNotFoundError,
    LifecycleTransitionError,
    ProviderNotFoundError,
)
from akaalEngine.extensions.integration.builtin_connection_bootstrap import (
    BUILTIN_CONNECTION_EXTENSION_ID,
    BuiltinConnectionBootstrap,
)
from akaalEngine.extensions.integration.connection_catalog_bridge import (
    ConnectionCatalogBridge,
    default_connection_catalog_bridge,
)
from akaalEngine.extensions.lifecycle.leases import HandleLeaseTracker, default_lease_tracker
from akaalEngine.extensions.lifecycle.manager import LifecycleManager, default_lifecycle_manager
from akaalEngine.extensions.lifecycle.notifications import NotificationDispatcher, default_notification_dispatcher
from akaalEngine.extensions.models.capability import CapabilityTruth
from akaalEngine.extensions.models.configuration import ConfigurationSchema
from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import (
    AuthorityId,
    ExtensionId,
    ProviderId,
    RegistryGeneration,
    StrategyId,
)
from akaalEngine.extensions.models.lifecycle import ExtensionLifecycleSnapshot
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.sanitized import (
    SanitizedConfigurationSchema,
    SanitizedExtensionDescriptor,
    SanitizedProviderDescriptor,
    SanitizedStrategyDescriptor,
)
from akaalEngine.extensions.models.provenance import PackageProvenance
from akaalEngine.extensions.models.strategy import StrategyContribution
from akaalEngine.extensions.resolution.handles import ResolvedStrategyHandle
from akaalEngine.extensions.resolution.resolver import StrategyResolver, default_strategy_resolver
from akaalEngine.extensions.supply_chain.trust_store import PublisherTrustStore
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
    default_contract_registry,
)
from akaalEngine.extensions.truth.availability_resolver import AvailabilityResolver
from akaalEngine.extensions.truth.capability_resolver import CapabilityTruthResolver

logger = logging.getLogger(__name__)


class ExtensionsAuthority:
    """
    Authority #2: Canonical Extensions Authority façade.
    Owns provider identity, versioning, strategy registration & resolution, dependency truth,
    configuration schemas, and drain-safe lifecycle management for all Engine authorities.
    """

    _instance: Optional[ExtensionsAuthority] = None
    _lock = threading.RLock()

    def __init__(
        self,
        registry: Optional[ExtensionRegistry] = None,
        contract_registry: Optional[AuthorityContractRegistry] = None,
        lifecycle_manager: Optional[LifecycleManager] = None,
        lease_tracker: Optional[HandleLeaseTracker] = None,
        strategy_resolver: Optional[StrategyResolver] = None,
        dep_inspector: Optional[DependencyInspector] = None,
        conn_bridge: Optional[ConnectionCatalogBridge] = None,
        notification_dispatcher: Optional[NotificationDispatcher] = None,
        auto_bootstrap: bool = True,
    ) -> None:
        self._registry = registry or default_extension_registry
        self._contract_registry = contract_registry or default_contract_registry
        self._lifecycle_mgr = lifecycle_manager or default_lifecycle_manager
        self._lease_tracker = lease_tracker or default_lease_tracker
        self._resolver = strategy_resolver or default_strategy_resolver
        self._dep_inspector = dep_inspector or default_dependency_inspector
        self._conn_bridge = conn_bridge or default_connection_catalog_bridge
        self._dispatcher = notification_dispatcher or default_notification_dispatcher

        if auto_bootstrap:
            self.bootstrap_builtin_providers()

    @classmethod
    def get_instance(cls) -> ExtensionsAuthority:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def bootstrap_builtin_providers(self) -> None:
        """Adopts the 28 frozen Connection providers into the Extensions registry."""
        with self._lock:
            manifest = BuiltinConnectionBootstrap.adopt_connection_providers(
                extension_registry=self._registry,
            )
            curr_state = self._lifecycle_mgr.get_state(manifest.extension_id)
            if curr_state != ExtensionLifecycleState.ACTIVE:
                gen = self._registry.get_generation()
                self._lifecycle_mgr.transition_state(
                    extension_id=manifest.extension_id,
                    new_state=ExtensionLifecycleState.REGISTERED,
                    generation=gen,
                    reason="Adoption of built-in Connection providers into registry",
                )
                self._lifecycle_mgr.transition_state(
                    extension_id=manifest.extension_id,
                    new_state=ExtensionLifecycleState.ACTIVE,
                    generation=gen,
                    reason="Automatic bootstrap activation of built-in providers",
                )

    # -------------------------------------------------------------------------
    # Public Gateway-Safe Query Operations
    # -------------------------------------------------------------------------

    def get_registry_generation(self) -> int:
        """Returns current monotonic registry generation integer."""
        return self._registry.get_generation().value

    def list_extensions(self) -> Sequence[SanitizedExtensionDescriptor]:
        """Returns sanitized descriptors for all installed extensions."""
        snapshot = self._registry.get_snapshot()
        descriptors: List[SanitizedExtensionDescriptor] = []
        for manifest in snapshot.list_all_extensions():
            desc = self._sanitize_manifest(manifest, snapshot)
            descriptors.append(desc)
        return tuple(descriptors)

    def describe_extension(self, extension_id: str | ExtensionId) -> Optional[SanitizedExtensionDescriptor]:
        """Returns sanitized descriptor for a specific extension ID."""
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        snapshot = self._registry.get_snapshot()
        manifest = snapshot.get_extension(ext_id)
        if manifest is None:
            return None
        return self._sanitize_manifest(manifest, snapshot)

    def list_providers(self) -> Sequence[str]:
        """Returns list of all registered provider IDs."""
        snapshot = self._registry.get_snapshot()
        return tuple(p.provider_id.value for p in snapshot.list_all_providers())

    def describe_provider(self, provider_id: str | ProviderId) -> Optional[SanitizedProviderDescriptor]:
        """Returns sanitized descriptor for a specific provider ID."""
        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        snapshot = self._registry.get_snapshot()
        prov = snapshot.get_provider(prov_id)
        if prov is None:
            return None
        return self._sanitize_provider(prov, snapshot)

    def get_dependency_diagnostics(self, provider_id: str | ProviderId) -> DependencyDiagnosticReport:
        """Runs isolated dependency inspection for a target provider."""
        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        snapshot = self._registry.get_snapshot()
        prov = snapshot.get_provider(prov_id)
        if prov is None:
            raise ProviderNotFoundError(f"Provider '{prov_id}' not found.")

        all_deps = list(prov.shared_dependencies)
        for strat in prov.strategies:
            all_deps.extend(strat.dependencies)

        return self._dep_inspector.inspect_all(prov_id.value, all_deps)

    def get_capability_truth(
        self,
        provider_id: str | ProviderId,
        authority_id: str | AuthorityId,
        capability_name: str,
    ) -> Optional[CapabilityTruth]:
        """Computes authoritative capability truth for a specific provider, authority, and capability."""
        prov_id = provider_id if isinstance(provider_id, ProviderId) else ProviderId(provider_id)
        auth_id = authority_id if isinstance(authority_id, AuthorityId) else AuthorityId(authority_id)

        snapshot = self._registry.get_snapshot()
        prov = snapshot.get_provider(prov_id)
        if prov is None:
            return None

        strat = prov.get_strategy_for_authority(auth_id)
        if strat is None:
            return None

        owning_ext = snapshot.get_provider_owner(prov_id)
        ext_state = self._lifecycle_mgr.get_state(owning_ext) if owning_ext else ExtensionLifecycleState.ACTIVE

        dep_report = self.get_dependency_diagnostics(prov_id)
        cap_decl = strat.get_capability_declaration(capability_name)

        return CapabilityTruthResolver.resolve_capability_truth(
            declaration=cap_decl,
            capability_name=capability_name,
            lifecycle_state=ext_state,
            dep_report=dep_report,
            proof_references=strat.proof_references,
        )

    def validate_configuration(
        self,
        schema: ConfigurationSchema,
        config_values: Mapping[str, Any],
        role: Optional[str] = None,
        active_capabilities: Optional[Sequence[str]] = None,
        context: Optional[Mapping[str, Any]] = None,
        strict_unknown: bool = False,
    ) -> None:
        """
        Validates configuration values against a ConfigurationSchema with condition context.
        Supports role and capability condition evaluation through canonical façade without exposing internals.
        """
        eval_ctx = dict(context or {})
        if role is not None:
            eval_ctx["active_role"] = role
        if active_capabilities is not None:
            eval_ctx["active_capabilities"] = tuple(active_capabilities)

        ConfigurationValidator.validate(
            schema=schema,
            config_values=config_values,
            context=eval_ctx,
            strict_unknown=strict_unknown,
        )

    # -------------------------------------------------------------------------
    # Lifecycle & Administrative Operations
    # -------------------------------------------------------------------------

    def register_extension(
        self,
        manifest: ExtensionManifest,
        allow_replace: bool = False,
        package_provenance: Optional[PackageProvenance] = None,
        package_artifact_bytes: Optional[bytes] = None,
        trust_store: Optional[PublisherTrustStore] = None,
    ) -> int:
        """
        Registers or replaces an extension manifest atomically.
        For manifests with origin=THIRD_PARTY_PACKAGE, package_provenance/package_artifact_bytes/
        trust_store are mandatory -- the underlying transaction fails closed without them.
        Returns the new published registry generation number.
        """
        # Check existing extension state for replacement
        existing = self._registry.get_snapshot().get_extension(manifest.extension_id)
        if existing is not None and allow_replace:
            curr_state = self._lifecycle_mgr.get_state(manifest.extension_id)
            if curr_state == ExtensionLifecycleState.FAULTED:
                raise LifecycleTransitionError(
                    f"Cannot replace faulted extension '{manifest.extension_id}' without operator recovery."
                )

        # Prepare any bridge mutations (e.g. Connection strategies)
        bridge_mutations: List[Callable[[], None]] = []
        bridge_rollbacks: List[Callable[[], None]] = []

        for prov in manifest.provider_contributions:
            for strat in prov.strategies:
                if strat.authority_id.value == "connection":
                    fwd, rb = self._conn_bridge.prepare_strategy_registration(strat, allow_replace=allow_replace)
                    bridge_mutations.append(fwd)
                    bridge_rollbacks.append(rb)

        new_snapshot = self._registry.register_extension(
            manifest=manifest,
            allow_replace=allow_replace,
            bridge_mutations=bridge_mutations,
            bridge_rollbacks=bridge_rollbacks,
            package_provenance=package_provenance,
            package_artifact_bytes=package_artifact_bytes,
            trust_store=trust_store,
        )

        # Update lifecycle state
        if existing is not None and allow_replace:
            # Atomic in-place replacement: preserves current lifecycle state (e.g. ACTIVE -> ACTIVE)
            self._lifecycle_mgr.record_replacement(
                extension_id=manifest.extension_id,
                generation=new_snapshot.generation,
                reason=f"Extension '{manifest.extension_id}' replaced/updated in generation {new_snapshot.generation.value}",
            )
        else:
            # Initial registration transitions to REGISTERED
            self._lifecycle_mgr.transition_state(
                extension_id=manifest.extension_id,
                new_state=ExtensionLifecycleState.REGISTERED,
                generation=new_snapshot.generation,
                reason="Extension registered in catalog",
            )

        return new_snapshot.generation.value

    def unregister_extension(self, extension_id: str | ExtensionId) -> int:
        """
        Unregisters an extension and removes it from the catalog.
        Rejects unregistration if active handle leases exist (drain safety).
        Returns the new published registry generation number.
        """
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        snapshot = self._registry.get_snapshot()
        manifest = snapshot.get_extension(ext_id)
        if manifest is None:
            raise ExtensionNotFoundError(f"Extension '{ext_id}' not found.")

        # Check active handle leases before unregistering
        active_count = self._lease_tracker.get_extension_active_count(ext_id)
        if active_count > 0:
            raise ExtensionHandleLeakError(
                f"Cannot unregister extension '{ext_id}': {active_count} active strategy handle leases exist. Must drain or release leases before removal."
            )

        # Prepare unregister bridge mutations and rollbacks
        bridge_mutations: List[Callable[[], None]] = []
        bridge_rollbacks: List[Callable[[], None]] = []
        for prov in manifest.provider_contributions:
            for strat in prov.strategies:
                if strat.authority_id.value == "connection":
                    fwd, rb = self._conn_bridge.prepare_strategy_unregistration(prov.provider_id)
                    bridge_mutations.append(fwd)
                    bridge_rollbacks.append(rb)

        new_snapshot = self._registry.unregister_extension(
            extension_id=ext_id,
            bridge_mutations=bridge_mutations,
            bridge_rollbacks=bridge_rollbacks,
        )

        self._lifecycle_mgr.transition_state(
            extension_id=ext_id,
            new_state=ExtensionLifecycleState.REMOVED,
            generation=new_snapshot.generation,
            reason="Extension unregistered from catalog",
        )

        return new_snapshot.generation.value

    def activate_extension(
        self,
        extension_id: str | ExtensionId,
        reason: str = "Operator activation",
    ) -> ExtensionLifecycleSnapshot:
        """Activates an extension, making its strategies available for resolution."""
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        return self._lifecycle_mgr.transition_state(
            extension_id=ext_id,
            new_state=ExtensionLifecycleState.ACTIVE,
            generation=self._registry.get_generation(),
            reason=reason,
        )

    def deactivate_extension(
        self,
        extension_id: str | ExtensionId,
        reason: str = "Operator deactivation",
    ) -> ExtensionLifecycleSnapshot:
        """Deactivates an extension, preventing new resolutions while allowing active handles to drain."""
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        return self._lifecycle_mgr.transition_state(
            extension_id=ext_id,
            new_state=ExtensionLifecycleState.INACTIVE,
            generation=self._registry.get_generation(),
            reason=reason,
        )

    def quarantine_extension(
        self,
        extension_id: str | ExtensionId,
        reason: str,
    ) -> ExtensionLifecycleSnapshot:
        """
        Forces an installed extension into FAULTED state outside the normal runtime-failure path --
        used when a signer certificate is revoked, a trust root is withdrawn, or an operator otherwise
        determines a previously-admitted package can no longer be trusted. FAULTED already blocks
        replacement without explicit operator recovery (see register_extension), so quarantine is a
        real, enforced restriction, not an advisory flag. Reachable from every non-terminal lifecycle
        state per the existing legal-transition table.
        """
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        return self._lifecycle_mgr.transition_state(
            extension_id=ext_id,
            new_state=ExtensionLifecycleState.FAULTED,
            generation=self._registry.get_generation(),
            reason=f"Quarantined: {reason}",
        )

    def get_lifecycle_snapshot(self, extension_id: str | ExtensionId) -> Optional[ExtensionLifecycleSnapshot]:
        """Returns lifecycle snapshot for an extension."""
        ext_id = extension_id if isinstance(extension_id, ExtensionId) else ExtensionId(extension_id)
        return self._lifecycle_mgr.get_snapshot(ext_id, self._registry.get_generation())

    # -------------------------------------------------------------------------
    # Internal Engine Operations (For Consuming Authorities)
    # -------------------------------------------------------------------------

    def register_authority_contract(self, contract: AuthorityContractDefinition) -> None:
        """Registers a contract definition for an Engine Authority."""
        self._contract_registry.register_contract(contract)

    def get_authority_contract(self, authority_id: str | AuthorityId) -> Optional[AuthorityContractDefinition]:
        """Returns the registered contract definition for an Engine Authority, if any."""
        auth_id = authority_id if isinstance(authority_id, AuthorityId) else AuthorityId(authority_id)
        return self._contract_registry.get_contract(auth_id)

    def inspect_strategy(
        self,
        provider_id: str | ProviderId,
        authority_id: str | AuthorityId,
        strategy_id: Optional[str | StrategyId] = None,
        required_contract_version: Optional[str] = None,
    ) -> SanitizedStrategyDescriptor:
        """
        Inspects provider/strategy metadata and declared capabilities WITHOUT instantiating
        or exposing executable physical authority.
        """
        return self._resolver.inspect_strategy(
            provider_id=provider_id,
            authority_id=authority_id,
            strategy_id=strategy_id,
            required_contract_version=required_contract_version,
        )

    def resolve_executable_strategy(
        self,
        provider_id: str | ProviderId,
        authority_id: str | AuthorityId,
        operation: str,
        strategy_id: Optional[str | StrategyId] = None,
        required_contract_version: Optional[str] = None,
        additional_required_capabilities: Optional[Sequence[str]] = None,
    ) -> ResolvedStrategyHandle:
        """
        Resolves an executable strategy handle.
        Security-critical: `operation` is strictly MANDATORY (no default None).
        The canonical authority maps `operation` to required capabilities and positively
        establishes them BEFORE physical strategy instantiation.
        """
        return self._resolver.resolve_executable_strategy(
            provider_id=provider_id,
            authority_id=authority_id,
            operation=operation,
            strategy_id=strategy_id,
            required_contract_version=required_contract_version,
            additional_required_capabilities=additional_required_capabilities,
        )

    def resolve_for_discovery(
        self,
        provider_id: str | ProviderId,
        operation: str = "SCHEMA_DISCOVERY",
        strategy_id: Optional[str | StrategyId] = None,
    ) -> ResolvedStrategyHandle:
        """Typed resolution for discovery operations with structural capability gating."""
        return self.resolve_executable_strategy(
            provider_id=provider_id,
            authority_id=AuthorityId("discovery"),
            operation=operation,
            strategy_id=strategy_id,
        )

    def resolve_for_cdc(
        self,
        provider_id: str | ProviderId,
        operation: str = "CDC_STREAM",
        strategy_id: Optional[str | StrategyId] = None,
    ) -> ResolvedStrategyHandle:
        """Typed resolution for CDC operations with structural capability gating."""
        return self.resolve_executable_strategy(
            provider_id=provider_id,
            authority_id=AuthorityId("cdc"),
            operation=operation,
            strategy_id=strategy_id,
        )

    def resolve_strategy(
        self,
        provider_id: str | ProviderId,
        authority_id: str | AuthorityId,
        strategy_id: Optional[str | StrategyId] = None,
        required_contract_version: Optional[str] = None,
        required_capabilities: Optional[Sequence[str]] = None,
    ) -> ResolvedStrategyHandle:
        """
        Resolves an executable strategy handle for a given provider and authority.
        Returns an internal ResolvedStrategyHandle with active lease token.
        """
        return self._resolver.resolve_strategy(
            provider_id=provider_id,
            authority_id=authority_id,
            strategy_id=strategy_id,
            required_contract_version=required_contract_version,
            required_capabilities=required_capabilities,
        )

    def release_strategy_handle(self, handle: ResolvedStrategyHandle) -> bool:
        """Releases an active strategy handle lease."""
        return handle.release()

    # -------------------------------------------------------------------------
    # Internal Sanitization Helpers
    # -------------------------------------------------------------------------

    def _sanitize_manifest(self, manifest: ExtensionManifest, snapshot: RegistrySnapshot) -> SanitizedExtensionDescriptor:
        providers = [self._sanitize_provider(p, snapshot) for p in manifest.provider_contributions]
        active_count = self._lease_tracker.get_extension_active_count(manifest.extension_id)
        state = self._lifecycle_mgr.get_state(manifest.extension_id)

        return SanitizedExtensionDescriptor(
            extension_id=manifest.extension_id.value,
            version=manifest.version,
            display_name=manifest.display_name,
            origin=manifest.origin.value,
            trust_tier=manifest.trust_tier.value,
            isolation_mode=manifest.isolation_mode.value,
            lifecycle_state=state.value,
            engine_version_range=manifest.engine_version_range.raw_expression,
            description=manifest.description,
            authors=manifest.authors,
            license=manifest.license,
            website=manifest.website,
            providers=tuple(providers),
            active_handle_count=active_count,
            registry_generation=snapshot.generation.value,
        )

    def _sanitize_provider(self, prov: ProviderContribution, snapshot: RegistrySnapshot) -> SanitizedProviderDescriptor:
        strategies = []
        for s in prov.strategies:
            schema_sanitized = None
            if s.configuration_schema:
                schema_sanitized = ConfigurationSanitizer.sanitize_schema(s.configuration_schema)
            strat_caps = [c.capability_name for c in s.capabilities if c.is_supported]
            strategies.append(
                SanitizedStrategyDescriptor(
                    strategy_id=s.strategy_id.value,
                    authority_id=s.authority_id.value,
                    provider_id=s.provider_id.value,
                    implementation_version=s.implementation_version,
                    contract_version_range=s.contract_version_range.raw_expression,
                    description=s.description,
                    capabilities=tuple(strat_caps),
                    configuration_schema=schema_sanitized,
                )
            )

        owning_ext = snapshot.get_provider_owner(prov.provider_id)
        ext_state = self._lifecycle_mgr.get_state(owning_ext) if owning_ext else ExtensionLifecycleState.ACTIVE
        dep_report = self.get_dependency_diagnostics(prov.provider_id)
        avail = AvailabilityResolver.resolve_availability(ext_state, dep_report)

        return SanitizedProviderDescriptor(
            provider_id=prov.provider_id.value,
            vendor_name=prov.vendor_name,
            display_name=prov.display_name,
            family=prov.family,
            version=prov.version,
            description=prov.description,
            supported_authorities=tuple(a.value for a in prov.get_all_authorities()),
            strategies=tuple(strategies),
            is_available=avail.is_available,
            lifecycle_state=ext_state.value,
            missing_dependencies=avail.missing_mandatory_dependencies,
        )


default_extensions_authority = ExtensionsAuthority.get_instance()
