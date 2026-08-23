"""
akaalEngine.extensions.integration.connection_contract
======================================================
Authority contract definition for Authority #1: Connection.
Validates that Connection strategy contributions inherit from BaseProviderStrategy.
"""

from __future__ import annotations

from typing import Any

from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.identity import AuthorityId
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
    default_contract_registry,
)

CONNECTION_AUTHORITY_ID = AuthorityId("connection")
CONNECTION_CONTRACT_VERSION = "1.0.0"


def validate_connection_strategy(instance: Any) -> bool:
    """Validates that a connection strategy conforms to the frozen BaseProviderStrategy SPI."""
    return isinstance(instance, BaseProviderStrategy)


def create_connection_contract_definition() -> AuthorityContractDefinition:
    """Creates the canonical AuthorityContractDefinition for Connection."""
    return AuthorityContractDefinition(
        authority_id=CONNECTION_AUTHORITY_ID,
        contract_version=CONNECTION_CONTRACT_VERSION,
        description="Authority #1 Connection: Physical establishment, session resets, driver management, probing",
        expected_base_type=BaseProviderStrategy,
        validator=validate_connection_strategy,
        known_capabilities=(
            "SCHEMA_DISCOVERY",
            "BULK_READ",
            "BULK_WRITE",
            "BINARY_COPY",
            "CDC_CAPTURE",
            "PARTITION_DISCOVERY",
            "IN_MEMORY_DB",
            "TLS_ENCRYPTION",
            "SSH_TUNNELING",
        ),
        compatibility_range=CompatibilityRange(">=1.0.0, <2.0.0"),
    )


def register_connection_contract(registry: AuthorityContractRegistry = default_contract_registry) -> None:
    """Registers the Connection contract into the global contract registry."""
    contract = create_connection_contract_definition()
    registry.register_contract(contract)
