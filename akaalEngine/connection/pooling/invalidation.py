"""
akaalEngine.connection.pooling.invalidation
===========================================
Pool invalidation coordinator reacting to secret rotation, identity drift, route change, and operator commands.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer

logger = logging.getLogger("akaalEngine.connection.pooling.invalidation")


class PoolInvalidationCoordinator:
    """
    Coordinates granular or system-wide pool invalidation across active connection pools.
    """

    def __init__(self, secret_consumer: Optional[SecretConsumer] = None) -> None:
        self.secret_consumer = secret_consumer or default_secret_consumer
        self._pool_invalidation_callbacks: List[Callable[[Optional[str], Optional[str]], None]] = []

        # Hook into secret consumer rotation notifications
        self.secret_consumer.register_rotation_listener(self._on_secret_rotated)

    def register_invalidation_listener(
        self,
        callback: Callable[[Optional[str], Optional[str]], None],  # (fingerprint_or_none, reason)
    ) -> None:
        """Registers a pool manager invalidation callback."""
        self._pool_invalidation_callbacks.append(callback)

    def _on_secret_rotated(self, secret_ref: str, new_version: str) -> None:
        """Invoked automatically when secret rotation is reported."""
        logger.info(
            f"[PoolInvalidationCoordinator] Invalidation triggered by secret rotation: ref='{secret_ref}', version='{new_version}'"
        )
        self.trigger_invalidation(fingerprint=None, reason=f"SECRET_ROTATED:{secret_ref}")

    def trigger_invalidation(
        self,
        fingerprint: Optional[str] = None,
        reason: str = "MANUAL_INVALIDATION",
    ) -> None:
        """
        Signals all registered pool listeners to invalidate matching pools.
        If fingerprint is None, invalidates all pools.
        """
        logger.info(
            f"[PoolInvalidationCoordinator] Triggering pool invalidation (fingerprint={fingerprint or 'ALL'}, reason='{reason}')."
        )
        for cb in self._pool_invalidation_callbacks:
            try:
                cb(fingerprint, reason)
            except Exception as exc:
                logger.error(f"[PoolInvalidationCoordinator] Error during pool invalidation callback: {exc}")


# Global default invalidation coordinator
default_invalidation_coordinator = PoolInvalidationCoordinator()
