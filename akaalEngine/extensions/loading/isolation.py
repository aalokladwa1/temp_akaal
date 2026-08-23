"""
akaalEngine.extensions.loading.isolation
========================================
Truthful reporting and verification of extension isolation modes.
Explicitly avoids claiming nonexistent sandboxing or remote worker boundaries.
"""

from __future__ import annotations

from typing import Mapping

from akaalEngine.extensions.errors.taxonomy import ExtensionRegistrationError
from akaalEngine.extensions.models.enums import IsolationMode, TrustTier


class IsolationManager:
    """
    Evaluates and reports truthful execution isolation capabilities.
    Enforces that only physically implemented isolation modes (IN_PROCESS) may be registered/activated.
    """

    @classmethod
    def verify_isolation_mode(
        cls,
        requested_mode: IsolationMode,
        trust_tier: TrustTier,
    ) -> IsolationMode:
        """
        Validates isolation mode against available engine capabilities.
        In P0-P4, only IN_PROCESS is physically implemented.
        SUBPROCESS, WASM, and REMOTE fail closed with ExtensionRegistrationError.
        """
        if requested_mode == IsolationMode.IN_PROCESS:
            return IsolationMode.IN_PROCESS

        raise ExtensionRegistrationError(
            f"Isolation mode '{requested_mode.value}' is not physically implemented in the Engine. Only 'IN_PROCESS' execution is supported."
        )
