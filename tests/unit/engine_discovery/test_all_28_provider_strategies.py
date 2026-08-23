"""
Unit tests validating all 28 concrete provider strategies conformance with BaseDiscoveryStrategy SPI.
"""

import pytest
from unittest.mock import MagicMock
from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy
from akaalEngine.discovery.strategies import ALL_DISCOVERY_STRATEGIES


@pytest.mark.parametrize("strat_cls", ALL_DISCOVERY_STRATEGIES)
def test_strategy_spi_compliance(strat_cls):
    strategy: BaseDiscoveryStrategy = strat_cls()
    assert isinstance(strategy, BaseDiscoveryStrategy)
    assert isinstance(strategy.provider_id, str)
    assert len(strategy.provider_id) > 0

    spec = EndpointSpec(
        provider_id=strategy.provider_id,
        host="localhost",
        database_name="test_db",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )

    ctx = DiscoveryContext()

    # 1. Identity discovery with empty/mock connection
    mock_conn = MagicMock()
    ident = strategy.discover_endpoint_identity(mock_conn, spec)
    assert ident is not None
    assert ident.provider_id == strategy.provider_id
    assert ident.version is not None

    # 2. Namespace discovery
    ns = strategy.discover_namespaces(mock_conn, spec, ctx)
    assert ns is not None
    assert isinstance(ns.schemas, tuple)

    # 3. Environment discovery
    env = strategy.discover_environment(mock_conn, spec, ctx)
    assert env is not None

    # 4. Topology discovery
    topo = strategy.discover_topology(mock_conn, spec, ctx)
    assert topo is not None
    assert isinstance(topo.nodes, tuple)

    # 5. CDC Prerequisites discovery
    cdc = strategy.discover_cdc_prerequisites(mock_conn, spec, ctx)
    assert cdc is not None

    # 6. Read-only permissions check
    perm = strategy.check_read_only_permissions(mock_conn, spec)
    assert perm is not None
