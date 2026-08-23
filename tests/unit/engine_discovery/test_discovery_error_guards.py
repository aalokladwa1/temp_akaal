"""
tests/unit/engine_discovery/test_discovery_error_guards.py
============================================================
Tests for CONS-004: Proves Discovery failure-path missing import guards
(DeterministicSampler and DiscoveryTimeoutError) execute without NameError.
"""

import pytest
from unittest.mock import MagicMock

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.authority import DiscoveryAuthority
from akaalEngine.discovery.core.executor import DiscoveryPipelineExecutor
from akaalEngine.discovery.errors.exceptions import DiscoveryTimeoutError
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.inventory import TableFacts


def test_sampling_failure_uses_deterministic_sampler_without_name_error():
    """Proves sampling exception in DiscoveryPipelineExecutor uses DeterministicSampler without NameError."""
    mock_strategy = MagicMock()
    mock_strategy.discover_endpoint_identity.return_value = None
    mock_strategy.discover_namespaces.return_value = MagicMock(schemas=["public"], default_schema="public", to_dict=lambda: {"schemas": ["public"]})
    mock_strategy.discover_objects_page.return_value = MagicMock(
        items=[TableFacts(name="t1", schema_name="public")],
        views=[],
        cursor=None,
        is_last_page=True,
    )
    mock_strategy.discover_objects_structure_bulk.return_value = {}
    mock_strategy.discover_table_statistics_bulk.return_value = {}
    mock_strategy.discover_permissions.return_value = None
    mock_strategy.discover_topology.return_value = None
    mock_strategy.discover_cdc_prerequisites.return_value = None
    mock_strategy.discover_environment.return_value = None
    mock_strategy.sample_data.side_effect = RuntimeError("Simulated sampling network error")
    mock_strategy.get_schema_change_marker.return_value = "m1"

    spec = EndpointSpec(provider_id="postgresql", host="localhost", port=5432, database_name="testdb")
    context = DiscoveryContext(sample_records=True, sample_size=10)

    # Should complete sampling failure without raising NameError for DeterministicSampler
    snapshot = DiscoveryPipelineExecutor.execute(
        strategy=mock_strategy,
        connection=MagicMock(),
        spec=spec,
        context=context,
    )

    assert "public.t1" in snapshot.sampled_data
    sample_set = snapshot.sampled_data["public.t1"]
    assert sample_set.is_sampled is False
    assert "Simulated sampling network error" in sample_set.error_message


def test_discovery_authority_timeout_catches_discovery_timeout_error(monkeypatch):
    """Proves DiscoveryAuthority.discover catches DiscoveryTimeoutError without NameError."""
    conn_auth = MagicMock()
    ext_auth = MagicMock()
    ext_auth.get_registry_generation.return_value = 1

    auth = DiscoveryAuthority(connection_authority=conn_auth, extensions_authority=ext_auth)

    mock_strategy = MagicMock()
    mock_handle = MagicMock()
    mock_lease = MagicMock()

    auth._coordinator = MagicMock()
    auth._coordinator.resolve_discovery_strategy.return_value = (mock_strategy, mock_handle)
    auth._coordinator.acquire_discovery_session.return_value = mock_lease

    monkeypatch.setattr(
        DiscoveryPipelineExecutor,
        "execute",
        MagicMock(side_effect=DiscoveryTimeoutError("Timed out")),
    )

    spec = EndpointSpec(provider_id="postgresql", host="localhost", port=5432, database_name="testdb")
    with pytest.raises(DiscoveryTimeoutError):
        auth.discover(spec, use_cache=False)

    auth._coordinator.invalidate_discovery_session.assert_called_once_with(mock_lease)
