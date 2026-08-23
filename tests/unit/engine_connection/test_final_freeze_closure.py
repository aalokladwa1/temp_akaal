from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.errors import ConfigurationError
from akaalEngine.connection.providers.relational import oracle as oracle_module
from akaalEngine.connection.providers.relational.oracle import OracleProviderStrategy
from akaalEngine.connection.providers.streaming.eventhubs import EventHubsProviderStrategy
from akaalEngine.connection.providers.streaming.pubsub import PubSubProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.extensions.integration.builtin_connection_schemas import (
    build_connection_provider_schema,
)


def test_eventhubs_validation_requires_supported_physical_probe():
    strategy = EventHubsProviderStrategy()
    assert strategy.validate(object()) is False

    client = MagicMock(spec=["get_eventhub_properties"])
    client.get_eventhub_properties.return_value = {"name": "orders"}
    assert strategy.validate(client) is True

    client.get_eventhub_properties.side_effect = RuntimeError("401 Unauthorized")
    assert strategy.validate(client) is False


@pytest.mark.parametrize("message", ["UNAUTHENTICATED", "HTTP 401 invalid credentials"])
def test_pubsub_authentication_failures_never_validate(message: str):
    strategy = PubSubProviderStrategy()
    client = MagicMock()
    client._akaal_project_id = "actual-project"
    client.list_topics.side_effect = RuntimeError(message)
    assert strategy.validate(client) is False


def test_pubsub_success_requires_real_project_scoped_rpc():
    strategy = PubSubProviderStrategy()
    client = MagicMock()
    client._akaal_project_id = "actual-project"
    client.list_topics.return_value = iter(())
    assert strategy.validate(client) is True
    client.list_topics.assert_called_once_with(
        project="projects/actual-project",
        timeout=5.0,
    )


def _oracle_spec(driver_mode: str) -> EndpointSpec:
    return EndpointSpec(
        provider_id="oracle",
        host="oracle.internal",
        port=1521,
        database_name="ORCLPDB1",
        options={"driver_mode": driver_mode},
    )


def _oracle_driver() -> MagicMock:
    driver = MagicMock()
    driver.is_thin_mode.return_value = True
    driver.makedsn.return_value = "dsn"
    driver.connect.return_value = MagicMock()
    return driver


def test_oracle_thin_never_initializes_thick_client():
    strategy = OracleProviderStrategy()
    driver = _oracle_driver()
    with patch.object(strategy, "is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"oracledb": driver}):
            strategy.connect(_oracle_spec("THIN"), ResolvedRoute("oracle.internal", 1521), {})
    driver.init_oracle_client.assert_not_called()
    driver.connect.assert_called_once()


def test_oracle_thick_initialization_is_once_only_and_thread_safe():
    strategy = OracleProviderStrategy()
    driver = _oracle_driver()
    oracle_module._ORACLE_THICK_INIT_CONFIG = None

    errors: list[BaseException] = []

    def connect() -> None:
        try:
            strategy.connect(_oracle_spec("THICK"), ResolvedRoute("oracle.internal", 1521), {})
        except BaseException as exc:  # pragma: no cover - assertion reports contents
            errors.append(exc)

    with patch.object(strategy, "is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"oracledb": driver}):
            threads = [threading.Thread(target=connect) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

    assert errors == []
    driver.init_oracle_client.assert_called_once_with()
    assert driver.connect.call_count == 8
    oracle_module._ORACLE_THICK_INIT_CONFIG = None


def test_oracle_thick_initialization_failure_is_preserved():
    strategy = OracleProviderStrategy()
    driver = _oracle_driver()
    driver.init_oracle_client.side_effect = RuntimeError("missing Oracle Client")
    oracle_module._ORACLE_THICK_INIT_CONFIG = None

    with patch.object(strategy, "is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"oracledb": driver}):
            with pytest.raises(ConfigurationError) as exc_info:
                strategy.connect(_oracle_spec("THICK"), ResolvedRoute("oracle.internal", 1521), {})

    assert exc_info.value.failure.error_code == "ORACLE_THICK_INITIALIZATION_FAILED"
    assert "missing Oracle Client" in exc_info.value.failure.message
    driver.connect.assert_not_called()
    oracle_module._ORACLE_THICK_INIT_CONFIG = None


def test_oracle_schema_exposes_only_explicit_driver_modes():
    schema = build_connection_provider_schema("oracle")
    field = schema.get_field("driver_mode")
    assert field is not None
    assert field.default_value == "THIN"
    assert field.constraint.allowed_values == ("THIN", "THICK")

