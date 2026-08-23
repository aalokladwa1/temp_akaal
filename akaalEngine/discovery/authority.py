"""
akaalEngine.discovery.authority
===============================
Canonical public façade for Authority #3 Discovery.
Coordinates physical endpoint introspection, 28-provider SPI strategies,
read-only session leases, composite-identity TTL caching, drift detection, and deterministic fingerprinting.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Mapping, Optional, Sequence, Type

from akaalEngine.connection.api.authority import ConnectionAuthority, default_connection_authority
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.core.cache import ProcessLocalDiscoveryCache, default_discovery_cache
from akaalEngine.discovery.core.coordinator import DiscoverySessionCoordinator
from akaalEngine.discovery.core.drift import DiscoveryDriftReport, MetadataDriftDetector
from akaalEngine.discovery.core.executor import DiscoveryPipelineExecutor
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.snapshot import DiscoverySnapshot
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy
from akaalEngine.discovery.strategies import ALL_DISCOVERY_STRATEGIES
from akaalEngine.extensions.authority import ExtensionsAuthority, default_extensions_authority
from akaalEngine.extensions.integration.builtin_connection_bootstrap import BUILTIN_CONNECTION_EXTENSION_ID
from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import AuthorityId, ExtensionId, ProviderId, StrategyId
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution
from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition

logger = logging.getLogger("akaalEngine.discovery.authority")


def compute_endpoint_fingerprint(spec: EndpointSpec) -> str:
    """Computes deterministic hash from sanitized endpoint specification."""
    raw_json = json.dumps(spec.sanitized_dict(), sort_keys=True)
    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()


class DiscoveryAuthority:
    """
    Public façade for Authority #3 Discovery.
    All external callers and downstream authorities (#4 Schema, #5 Durability, etc.)
    interact strictly through this class.
    """

    def __init__(
        self,
        connection_authority: Optional[ConnectionAuthority] = None,
        extensions_authority: Optional[ExtensionsAuthority] = None,
        cache: Optional[ProcessLocalDiscoveryCache] = None,
    ) -> None:
        self._conn_auth = connection_authority or default_connection_authority
        self._ext_auth = extensions_authority or default_extensions_authority
        self._cache = cache or default_discovery_cache
        self._coordinator = DiscoverySessionCoordinator(
            connection_authority=self._conn_auth,
            extensions_authority=self._ext_auth,
        )
        self._bootstrap_strategies()

    def _bootstrap_strategies(self) -> None:
        """Ensures the discovery contract and 28 default strategies are registered in Extensions."""
        auth_id = AuthorityId("discovery")
        contract = AuthorityContractDefinition(
            authority_id=auth_id,
            contract_version="1.0.0",
            description="SPI contract for physical endpoint metadata discovery.",
            expected_base_type=BaseDiscoveryStrategy,
        )
        self._ext_auth.register_authority_contract(contract)

        # Map strategies by provider id string
        strat_map: dict[str, Type[BaseDiscoveryStrategy]] = {
            strat_cls().provider_id: strat_cls for strat_cls in ALL_DISCOVERY_STRATEGIES
        }

        # Augment existing adopted providers in Extensions catalog
        snapshot = self._ext_auth._registry.get_snapshot()
        conn_manifest = snapshot.get_extension(BUILTIN_CONNECTION_EXTENSION_ID)

        if conn_manifest:
            has_discovery = any(
                s.authority_id.value == "discovery"
                for prov in conn_manifest.provider_contributions
                for s in prov.strategies
            )
            if has_discovery:
                return  # Already bootstrapped

        updated_providers = []
        if conn_manifest:
            for prov in conn_manifest.provider_contributions:
                p_str = prov.provider_id.value
                strategies = list(prov.strategies)
                if p_str in strat_map:
                    strat_cls = strat_map[p_str]
                    strat_contrib = StrategyContribution(
                        strategy_id=StrategyId(f"{p_str}_discovery"),
                        authority_id=auth_id,
                        provider_id=prov.provider_id,
                        contract_version_range=CompatibilityRange(">=1.0.0"),
                        strategy_factory=strat_cls,
                        implementation_version="1.0.0",
                    )
                    strategies.append(strat_contrib)

                updated_providers.append(
                    ProviderContribution(
                        provider_id=prov.provider_id,
                        vendor_name=prov.vendor_name,
                        display_name=prov.display_name,
                        family=prov.family,
                        version=prov.version,
                        description=prov.description,
                        strategies=tuple(strategies),
                        shared_configuration_schema=prov.shared_configuration_schema,
                        shared_dependencies=prov.shared_dependencies,
                        capabilities=prov.capabilities,
                    )
                )

            updated_manifest = ExtensionManifest(
                extension_id=conn_manifest.extension_id,
                version=conn_manifest.version,
                display_name=conn_manifest.display_name,
                engine_version_range=conn_manifest.engine_version_range,
                origin=conn_manifest.origin,
                trust_tier=conn_manifest.trust_tier,
                isolation_mode=conn_manifest.isolation_mode,
                description=conn_manifest.description,
                authors=conn_manifest.authors,
                license=conn_manifest.license,
                website=conn_manifest.website,
                provider_contributions=tuple(updated_providers),
            )

            try:
                self._ext_auth.register_extension(updated_manifest, allow_replace=True)
            except Exception as exc:
                logger.debug(f"Discovery extension registration: {exc}")

    def discover(
        self,
        spec: EndpointSpec,
        context: Optional[DiscoveryContext] = None,
        use_cache: bool = True,
    ) -> DiscoverySnapshot:
        """
        Executes comprehensive physical discovery against the specified endpoint.
        Guarantees strategy-handle and session-lease cleanup across all success and failure exit paths.
        """
        ctx = context or DiscoveryContext()
        spec_fp = compute_endpoint_fingerprint(spec)
        reg_gen = self._ext_auth.get_registry_generation()
        cache_key = self._cache.generate_key_from_context(spec_fp, ctx, registry_generation=reg_gen)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # 1. Resolve strategy from Extensions (outermost lifecycle boundary)
        strategy, handle = self._coordinator.resolve_discovery_strategy(spec.provider_id)
        timed_out = False
        try:
            # 2. Acquire read-only session lease from Connection Authority
            lease = self._coordinator.acquire_discovery_session(
                spec=spec,
                timeout_seconds=ctx.timeout_seconds,
            )
            try:
                raw_conn = lease.get_physical_handle()
                # 3. Execute Discovery Pipeline
                snapshot = DiscoveryPipelineExecutor.execute(
                    strategy=strategy,
                    connection=raw_conn,
                    spec=spec,
                    context=ctx,
                    route=None,
                )

                if snapshot.warnings and any("timed out" in w.lower() or "deadline" in w.lower() for w in snapshot.warnings):
                    timed_out = True

                # Store in cache
                if use_cache and snapshot.completeness.value != "FAILED":
                    self._cache.put(cache_key, snapshot, ttl_seconds=300.0)

                return snapshot
            except DiscoveryTimeoutError:
                timed_out = True
                raise
            except Exception:
                raise
            finally:
                if timed_out:
                    self._coordinator.invalidate_discovery_session(lease)
                else:
                    self._coordinator.release_discovery_session(lease)
        finally:
            self._coordinator.release_strategy_handle(handle)

    def sample(
        self,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        limit: int = 100,
        timeout_seconds: float = 3.0,
    ) -> SampledRecordSet:
        """
        Executes bounded, low-impact preview sampling on an object with sensitive data redaction.
        Guarantees deterministic cleanup across all failure paths.
        """
        strategy, handle = self._coordinator.resolve_discovery_strategy(spec.provider_id)
        timed_out = False
        try:
            lease = self._coordinator.acquire_discovery_session(spec=spec, timeout_seconds=timeout_seconds + 5.0)
            try:
                raw_conn = lease.get_physical_handle()
                sample_res = strategy.sample_data(
                    connection=raw_conn,
                    spec=spec,
                    schema_name=schema_name,
                    table_name=table_name,
                    limit=limit,
                    timeout_seconds=timeout_seconds,
                )
                if not sample_res.is_sampled and sample_res.error_message and "timed out" in sample_res.error_message.lower():
                    timed_out = True
                return sample_res
            except Exception:
                timed_out = True
                raise
            finally:
                if timed_out:
                    self._coordinator.invalidate_discovery_session(lease)
                else:
                    self._coordinator.release_discovery_session(lease)
        finally:
            self._coordinator.release_strategy_handle(handle)

    def detect_drift(
        self,
        baseline_snapshot: DiscoverySnapshot,
        spec: EndpointSpec,
        context: Optional[DiscoveryContext] = None,
    ) -> DiscoveryDriftReport:
        """
        Compares a historical baseline snapshot against live metadata to detect structural mutations.
        """
        current_snapshot = self.discover(spec, context, use_cache=False)
        if not baseline_snapshot.fingerprint or not current_snapshot.fingerprint:
            baseline_fp = baseline_snapshot.compute_sha256_fingerprint()
            current_fp = current_snapshot.compute_sha256_fingerprint()
        else:
            baseline_fp = baseline_snapshot.fingerprint
            current_fp = current_snapshot.fingerprint

        return MetadataDriftDetector.compare_fingerprints(baseline_fp, current_fp)

    def invalidate_cache(self, spec: EndpointSpec, scope: Optional[DiscoveryScope] = None) -> int:
        """Invalidates cached discovery snapshots for an endpoint."""
        spec_fp = compute_endpoint_fingerprint(spec)
        count = 0
        with self._cache._lock:
            for k in list(self._cache._cache.keys()):
                if k.startswith(spec_fp[:16]):
                    self._cache.invalidate(k)
                    count += 1
        return count


default_discovery_authority = DiscoveryAuthority()
