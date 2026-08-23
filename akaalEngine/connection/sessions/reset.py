"""
akaalEngine.connection.sessions.reset
=====================================
Deterministic session reset, rollback enforcement, and cleanliness verification.
Guarantees dirty, uncommitted, or poisoned sessions are never returned to reusable pools.
"""

from __future__ import annotations

import logging
from typing import Optional

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    SessionPoisonedError,
)
from akaalEngine.connection.models.session import InternalSessionHandle, SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy

logger = logging.getLogger("akaalEngine.connection.sessions.reset")


class SessionResetManager:
    """
    Coordinates physical session reset, transactional rollback, and cleanliness validation.
    """

    @classmethod
    def reset_and_clean_session(
        cls,
        handle: InternalSessionHandle,
        strategy: BaseProviderStrategy,
    ) -> bool:
        """
        Resets a session back to a pristine state.
        Returns True if session is clean and reusable, False if it was destroyed.
        """
        if handle.is_closed:
            return False

        if handle.is_poisoned:
            cls.destroy_poisoned_session(handle, strategy)
            return False

        previous_purpose = handle.purpose
        conn = handle.physical_connection

        try:
            # 1. Ask provider strategy to reset physical session
            is_clean = strategy.reset_session(conn, previous_purpose)
            if not is_clean:
                logger.warning(
                    f"[SessionResetManager] Provider '{handle.provider_id}' failed session reset for session '{handle.session_id}'. Destroying connection."
                )
                cls.destroy_poisoned_session(handle, strategy)
                return False

            # 2. Clear borrower state and variables
            handle.owner_lease_id = None
            handle.session_variables.clear()
            handle.in_transaction = False
            return True

        except Exception as exc:
            logger.error(
                f"[SessionResetManager] Exception during session reset for '{handle.session_id}': {exc}. Destroying connection."
            )
            cls.destroy_poisoned_session(handle, strategy)
            return False

    @classmethod
    def destroy_poisoned_session(
        cls,
        handle: InternalSessionHandle,
        strategy: BaseProviderStrategy,
    ) -> None:
        """Destroys physical connection, closes associated route tunnels, and marks handle closed."""
        handle.is_poisoned = True
        handle.is_closed = True
        try:
            handle.close_route()
        except Exception:
            pass
        try:
            if handle.physical_connection is not None:
                strategy.close(handle.physical_connection)
        except Exception:
            pass
        handle.physical_connection = None
        handle.route_resource = None
