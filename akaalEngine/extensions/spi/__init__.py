"""
akaalEngine.extensions.spi
==========================
Service Provider Interfaces (SPI) for Authority contracts, Strategy factories, and Provider bundles.
"""

from akaalEngine.extensions.spi.strategy_factory import (
    InstanceStrategyFactory,
    LazyTypeStrategyFactory,
    StrategyFactory,
)
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
    default_contract_registry,
)
from akaalEngine.extensions.spi.provider_bundle import (
    ProviderBundle,
)
from akaalEngine.extensions.spi.validators import (
    ManifestValidator,
)

__all__ = [
    "StrategyFactory",
    "InstanceStrategyFactory",
    "LazyTypeStrategyFactory",
    "AuthorityContractDefinition",
    "AuthorityContractRegistry",
    "default_contract_registry",
    "ProviderBundle",
    "ManifestValidator",
]
