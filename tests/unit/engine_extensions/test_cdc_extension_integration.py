"""
tests.unit.engine_extensions.test_cdc_extension_integration
==============================================================
P7A.4: CDC authority <-> Extensions authority integration, and the negative-capability
enforcement gate (ResolvedStrategyHandle.require_capability). Real CDCAuthority, real
ExtensionsAuthority, real ICDCSourceAdapter implementations -- no mocks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.cdc.capture.base import ICDCSourceAdapter
from akaalEngine.cdc.models.capabilities import (
    CDCCapabilityDescriptor,
    HandshakeMode,
    MigrationMode,
    OrderingGuarantee,
    SynchronizationBarrierStrategy,
)
from akaalEngine.cdc.models.event import ChangeEvent
from akaalEngine.cdc.models.position import CDCSourcePosition, PollingWatermarkPosition
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.errors.taxonomy import CapabilityNotSupportedError, ExtensionEngineException, StrategyNotFoundError
from akaalEngine.extensions.lifecycle.manager import LifecycleManager
from akaalEngine.extensions.resolution.resolver import StrategyResolver
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)


class _StubCDCAdapter(ICDCSourceAdapter):
    """Minimal real ICDCSourceAdapter -- not a mock, a genuine (if trivial) implementation."""

    @property
    def engine_name(self) -> str:
        return "STUBDB"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="STUBDB",
            capture_mode=MigrationMode.ONLINE_NATIVE_CDC,
            handshake_mode=HandshakeMode.BEST_EFFORT_HANDSHAKE,
            barrier_strategy=SynchronizationBarrierStrategy.PROVIDER_NATIVE_WATERMARK,
            ordering_guarantee=OrderingGuarantee.PROVIDER_DEFINED,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True}

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        pass

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        return []

    def get_current_position(self) -> CDCSourcePosition:
        return PollingWatermarkPosition(watermark_val=0, polling_type="STUBDB")

    def close(self) -> None:
        pass


def _register_cdc_provider(
    ext_auth: ExtensionsAuthority,
    ext_id: str,
    provider_id: str,
    cdc_supported: bool,
) -> None:
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{provider_id}-cdc-strat"),
        authority_id=AuthorityId("cdc"),
        provider_id=ProviderId(provider_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_StubCDCAdapter,
        capabilities=(
            CapabilityDeclaration(capability_name="CDC_CAPTURE", is_supported=cdc_supported),
        ),
    )
    prov = ProviderContribution(
        provider_id=ProviderId(provider_id),
        vendor_name="StubVendor",
        display_name="Stub Provider",
        family="nosql",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId(ext_id),
        version="1.0.0",
        display_name=f"Extension {ext_id}",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )
    ext_auth.register_extension(manifest)
    ext_auth.activate_extension(ext_id)


def _fresh_authority() -> ExtensionsAuthority:
    """
    Builds a fully isolated ExtensionsAuthority backed by brand-new (non-singleton) registry
    and lifecycle-manager instances, threaded through to its own internal StrategyResolver too --
    never touches the process-global defaults, which other tests in this session rely on staying
    at exactly the 28 built-in connection providers. (ExtensionsAuthority.register_extension()/
    activate_extension() operate through self._registry/self._lifecycle_mgr directly, but its
    resolve_strategy() delegates to a StrategyResolver with its OWN default registry/lifecycle-manager
    references unless explicitly given the same fresh instances -- both must be shared explicitly.)
    """
    fresh_registry = ExtensionRegistry()
    fresh_lifecycle_mgr = LifecycleManager()
    fresh_resolver = StrategyResolver(registry=fresh_registry, lifecycle_manager=fresh_lifecycle_mgr)
    ext_auth = ExtensionsAuthority(
        registry=fresh_registry,
        lifecycle_manager=fresh_lifecycle_mgr,
        strategy_resolver=fresh_resolver,
        auto_bootstrap=False,
    )
    CDCAuthority(extensions_authority=ext_auth)  # registers the "cdc" authority contract as a side effect
    return ext_auth


def test_cdc_authority_without_extensions_authority_rejects_resolve_call():
    cdc = CDCAuthority()  # no extensions_authority
    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider("anything")


def test_cdc_authority_resolves_real_extension_registered_adapter():
    ext_auth = _fresh_authority()
    _register_cdc_provider(ext_auth, "ext.stubdb", "stubdb-provider", cdc_supported=True)

    cdc = CDCAuthority(extensions_authority=ext_auth)
    handle = cdc.resolve_adapter_for_provider("stubdb-provider")
    try:
        assert isinstance(cdc.active_adapter, _StubCDCAdapter)
        assert cdc.active_adapter.engine_name == "STUBDB"
        # The mechanism is real, not a metadata stub -- prove the adapter actually works.
        assert cdc.active_adapter.fetch_events() == []
    finally:
        handle.release()


def test_negative_cdc_capability_declaration_blocks_resolution_when_required():
    """A connector declaring CDC_CAPTURE=NO cannot be resolved when that capability is required."""
    ext_auth = _fresh_authority()
    _register_cdc_provider(ext_auth, "ext.nocdc", "nocdc-provider", cdc_supported=False)

    cdc = CDCAuthority(extensions_authority=ext_auth)
    with pytest.raises(StrategyNotFoundError):
        cdc.resolve_adapter_for_provider("nocdc-provider", required_capability="CDC_CAPTURE")


def test_negative_cdc_capability_declaration_blocks_post_hoc_gate_even_if_resolved_without_requirement():
    """
    Even if a caller resolves WITHOUT declaring required_capability up front, the returned
    handle's require_capability() gate independently and correctly rejects the unsupported
    capability -- proving the gate is a real, self-contained enforcement primitive, not
    something that only works when the resolver's optional filter happens to be used.
    """
    ext_auth = _fresh_authority()
    _register_cdc_provider(ext_auth, "ext.nocdc2", "nocdc-provider-2", cdc_supported=False)

    handle = ext_auth.resolve_strategy(provider_id="nocdc-provider-2", authority_id="cdc")
    try:
        assert handle.is_capability_supported("CDC_CAPTURE") is False
        with pytest.raises(CapabilityNotSupportedError):
            handle.require_capability("CDC_CAPTURE")
    finally:
        handle.release()


def test_positive_capability_gate_passes_and_returns_truth():
    ext_auth = _fresh_authority()
    _register_cdc_provider(ext_auth, "ext.yescdc", "yescdc-provider", cdc_supported=True)

    handle = ext_auth.resolve_strategy(provider_id="yescdc-provider", authority_id="cdc")
    try:
        truth = handle.require_capability("CDC_CAPTURE")
        assert truth.is_supported is True
    finally:
        handle.release()


def test_undeclared_capability_is_treated_as_unsupported_not_silently_allowed():
    """Silence (no declaration at all) must be treated identically to an explicit is_supported=False."""
    ext_auth = _fresh_authority()
    _register_cdc_provider(ext_auth, "ext.undeclared", "undeclared-provider", cdc_supported=True)  # only declares CDC_CAPTURE

    handle = ext_auth.resolve_strategy(provider_id="undeclared-provider", authority_id="cdc")
    try:
        with pytest.raises(CapabilityNotSupportedError):
            handle.require_capability("SOME_OTHER_CAPABILITY_NEVER_DECLARED")
    finally:
        handle.release()


def test_resolved_adapter_fails_contract_if_not_real_icdcsourceadapter():
    """A strategy_factory that doesn't produce an ICDCSourceAdapter is rejected, not silently accepted."""
    ext_auth = _fresh_authority()
    strat = StrategyContribution(
        strategy_id=StrategyId("bad-cdc-strat"),
        authority_id=AuthorityId("cdc"),
        provider_id=ProviderId("bad-provider"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),  # not an ICDCSourceAdapter
    )
    prov = ProviderContribution(
        provider_id=ProviderId("bad-provider"), vendor_name="V", display_name="P",
        family="nosql", strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.bad"), version="1.0.0", display_name="Bad Ext",
        engine_version_range=CompatibilityRange(">=1.0.0"), provider_contributions=(prov,),
    )
    ext_auth.register_extension(manifest)
    ext_auth.activate_extension("ext.bad")

    cdc = CDCAuthority(extensions_authority=ext_auth)
    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider("bad-provider")
