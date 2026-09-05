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

    _PHYSICALLY_IMPLEMENTED = (IsolationMode.IN_PROCESS, IsolationMode.SUBPROCESS)

    @classmethod
    def verify_isolation_mode(
        cls,
        requested_mode: IsolationMode,
        trust_tier: TrustTier,
    ) -> IsolationMode:
        """
        Validates isolation mode against available engine capabilities.
        IN_PROCESS (no isolation, engine's own process) and SUBPROCESS (real separate OS
        process, see akaalEngine.extensions.sandbox.process_isolation.SubprocessSandbox)
        are physically implemented. WASM and REMOTE fail closed: no WASM runtime is
        installed and no remote worker infrastructure exists in this repository.
        """
        if requested_mode in cls._PHYSICALLY_IMPLEMENTED:
            return requested_mode

        raise ExtensionRegistrationError(
            f"Isolation mode '{requested_mode.value}' is not physically implemented in the Engine. "
            f"Only {', '.join(m.value for m in cls._PHYSICALLY_IMPLEMENTED)} execution is supported."
        )
