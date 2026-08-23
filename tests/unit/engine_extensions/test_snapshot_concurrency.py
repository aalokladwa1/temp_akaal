"""
tests.unit.engine_extensions.test_snapshot_concurrency
======================================================
Tests verifying thread safety between concurrent readers reading immutable snapshots and background writers.
"""

import threading
import time
import pytest
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)


def test_concurrent_readers_and_writers():
    default_contract_registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )
    reg = ExtensionRegistry()
    stop_event = threading.Event()
    read_counts = [0]
    errors = []

    def reader_loop():
        while not stop_event.is_set():
            try:
                snap = reg.get_snapshot()
                # Verify snapshot consistency
                _ = len(snap.list_all_extensions())
                read_counts[0] += 1
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=reader_loop) for _ in range(4)]
    for t in threads:
        t.start()

    # Writer performs several atomic registrations
    for i in range(10):
        strat = StrategyContribution(
            strategy_id=StrategyId(f"s-{i}"),
            authority_id=AuthorityId("transport"),
            provider_id=ProviderId(f"p-{i}"),
            contract_version_range=CompatibilityRange("*"),
            strategy_factory=lambda: object(),
        )
        prov = ProviderContribution(
            provider_id=ProviderId(f"p-{i}"),
            vendor_name="Vendor",
            display_name=f"Provider {i}",
            family="storage",
            strategies=(strat,),
        )
        manifest = ExtensionManifest(
            extension_id=ExtensionId(f"ext-{i}"),
            version="1.0.0",
            display_name=f"Extension {i}",
            engine_version_range=CompatibilityRange(">=1.0.0"),
            provider_contributions=(prov,),
        )
        reg.register_extension(manifest)
        time.sleep(0.01)

    stop_event.set()
    for t in threads:
        t.join()

    assert not errors
    assert read_counts[0] > 0
    assert reg.get_generation().value == 11
    assert len(reg.get_snapshot().list_all_extensions()) == 10
