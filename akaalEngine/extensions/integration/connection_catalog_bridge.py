"""
akaalEngine.extensions.integration.connection_catalog_bridge
============================================================
Transactional bridge between Extensions Authority and frozen Connection ProviderCatalog.
Coordinates provider strategy registration, replacement, and unregistration, ensuring
Connection catalog generation increments and pool invalidations propagate without duplicating algorithms.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

from akaalEngine.connection.catalog.provider_catalog import (
    ProviderCatalog,
    default_provider_catalog,
)
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.extensions.errors.taxonomy import (
    AuthorityContractMismatchError,
    ExtensionRegistrationError,
)
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId, StrategyId
from akaalEngine.extensions.models.strategy import StrategyContribution

logger = logging.getLogger(__name__)


class ConnectionCatalogBridge:
    """
    Bridge coordinating Connection ProviderCatalog mutations from Extensions.
    """

    def __init__(self, connection_catalog: Optional[ProviderCatalog] = None) -> None:
        self._connection_catalog = connection_catalog or default_provider_catalog

    def prepare_strategy_registration(
        self,
        strategy_contrib: StrategyContribution,
        allow_replace: bool = False,
    ) -> Tuple[Callable[[], None], Callable[[], None]]:
        """
        Prepares forward and rollback mutation closures for registering a Connection strategy.
        Instantiates external callable factories strictly inside the forward mutation closure
        only after manifest admission has succeeded.
        """
        if strategy_contrib.authority_id.value != "connection":
            # No-op for other authorities
            return (lambda: None, lambda: None)

        prov_id_str = strategy_contrib.provider_id.value
        try:
            old_strategy = self._connection_catalog.get_strategy(prov_id_str)
        except Exception:
            old_strategy = None

        def forward_mutation() -> None:
            # Instantiate strategy lazily at bridge execution time
            if callable(strategy_contrib.strategy_factory):
                try:
                    inst = strategy_contrib.strategy_factory()
                except Exception as exc:
                    from akaalEngine.extensions.errors.taxonomy import StrategyInstantiationError
                    raise StrategyInstantiationError(
                        f"Failed to instantiate strategy '{strategy_contrib.strategy_id}': {exc}"
                    ) from exc
            else:
                inst = strategy_contrib.strategy_factory

            if not isinstance(inst, BaseProviderStrategy):
                raise AuthorityContractMismatchError(
                    f"Cannot bridge strategy '{strategy_contrib.strategy_id}' to Connection: "
                    f"instance of type '{type(inst).__name__}' does not inherit from BaseProviderStrategy."
                )

            logger.info("Bridging strategy '%s' into Connection ProviderCatalog (allow_override=%s)", prov_id_str, allow_replace)
            self._connection_catalog.register_provider(inst, allow_override=allow_replace)
            if old_strategy is not None and allow_replace:
                from akaalEngine.connection.pooling.invalidation import default_invalidation_coordinator
                default_invalidation_coordinator.trigger_invalidation(
                    fingerprint=None,
                    reason=f"Provider strategy '{prov_id_str}' replaced via Extensions.",
                )

        def rollback_mutation() -> None:
            if old_strategy is not None:
                logger.info("Rolling back Connection ProviderCatalog for '%s'", prov_id_str)
                self._connection_catalog.register_provider(old_strategy, allow_override=True)
            else:
                try:
                    self._connection_catalog.unregister_provider(prov_id_str)
                except Exception:
                    pass

        return (forward_mutation, rollback_mutation)

    def prepare_strategy_unregistration(
        self,
        provider_id: ProviderId,
    ) -> Tuple[Callable[[], None], Callable[[], None]]:
        """Prepares unregistration forward and rollback mutation closures for a Connection provider."""
        prov_id_str = provider_id.value
        try:
            old_strategy = self._connection_catalog.get_strategy(prov_id_str)
        except Exception:
            old_strategy = None

        def forward_mutation() -> None:
            removed = self._connection_catalog.unregister_provider(prov_id_str)
            if not removed and old_strategy is not None:
                raise RuntimeError(f"Failed to unregister provider '{prov_id_str}' from Connection ProviderCatalog.")

        def rollback_mutation() -> None:
            if old_strategy is not None:
                logger.info("Rolling back unregistration for '%s' in Connection ProviderCatalog", prov_id_str)
                self._connection_catalog.register_provider(old_strategy, allow_override=True)

        return (forward_mutation, rollback_mutation)


default_connection_catalog_bridge = ConnectionCatalogBridge()
