"""
akaalEngine.extensions.integration
==================================
Integration contracts, catalog bridge, and bootstrap adoption for Authority #1 Connection.
"""

from akaalEngine.extensions.integration.connection_contract import (
    CONNECTION_AUTHORITY_ID,
    CONNECTION_CONTRACT_VERSION,
    AuthorityContractDefinition,
    create_connection_contract_definition,
    register_connection_contract,
    validate_connection_strategy,
)
from akaalEngine.extensions.integration.connection_catalog_bridge import (
    ConnectionCatalogBridge,
    default_connection_catalog_bridge,
)
from akaalEngine.extensions.integration.builtin_connection_bootstrap import (
    BUILTIN_CONNECTION_EXTENSION_ID,
    BuiltinConnectionBootstrap,
)

__all__ = [
    "CONNECTION_AUTHORITY_ID",
    "CONNECTION_CONTRACT_VERSION",
    "AuthorityContractDefinition",
    "validate_connection_strategy",
    "create_connection_contract_definition",
    "register_connection_contract",
    "ConnectionCatalogBridge",
    "default_connection_catalog_bridge",
    "BUILTIN_CONNECTION_EXTENSION_ID",
    "BuiltinConnectionBootstrap",
]
