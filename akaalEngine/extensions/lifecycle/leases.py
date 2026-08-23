"""
akaalEngine.extensions.lifecycle.leases
=======================================
Tracks active strategy handle leases to enable drain-safe deactivation and prevent use-after-unload.
Thread-safe accounting prevents corrupt counters on duplicate or stale releases.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from akaalEngine.extensions.errors.taxonomy import ExtensionHandleLeakError
from akaalEngine.extensions.models.identity import ExtensionId, StrategyId


@dataclass(frozen=True)
class LeaseToken:
    """Unique immutable token representing a checked-out strategy handle lease."""
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    extension_id: ExtensionId = field(default_factory=lambda: ExtensionId("unknown"))
    strategy_id: StrategyId = field(default_factory=lambda: StrategyId("unknown"))


class HandleLeaseTracker:
    """
    Thread-safe tracker of active strategy handle leases.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_leases: Dict[str, LeaseToken] = {}
        self._extension_counts: Dict[ExtensionId, int] = {}
        self._strategy_counts: Dict[StrategyId, int] = {}

    def acquire_lease(self, extension_id: ExtensionId, strategy_id: StrategyId) -> LeaseToken:
        """Acquires and registers a new active handle lease."""
        token = LeaseToken(extension_id=extension_id, strategy_id=strategy_id)
        with self._lock:
            self._active_leases[token.token_id] = token
            self._extension_counts[extension_id] = self._extension_counts.get(extension_id, 0) + 1
            self._strategy_counts[strategy_id] = self._strategy_counts.get(strategy_id, 0) + 1
        return token

    def release_lease(self, token: LeaseToken) -> bool:
        """
        Releases an active handle lease.
        Returns True if successfully released; returns False if token was already released or unknown.
        """
        with self._lock:
            if token.token_id not in self._active_leases:
                return False  # Already released or invalid; fail-safe without corrupting counters

            del self._active_leases[token.token_id]

            ext_id = token.extension_id
            if ext_id in self._extension_counts:
                self._extension_counts[ext_id] = max(0, self._extension_counts[ext_id] - 1)
                if self._extension_counts[ext_id] == 0:
                    del self._extension_counts[ext_id]

            strat_id = token.strategy_id
            if strat_id in self._strategy_counts:
                self._strategy_counts[strat_id] = max(0, self._strategy_counts[strat_id] - 1)
                if self._strategy_counts[strat_id] == 0:
                    del self._strategy_counts[strat_id]

            return True

    def get_extension_active_count(self, extension_id: ExtensionId) -> int:
        with self._lock:
            return self._extension_counts.get(extension_id, 0)

    def get_strategy_active_count(self, strategy_id: StrategyId) -> int:
        with self._lock:
            return self._strategy_counts.get(strategy_id, 0)

    def get_total_active_count(self) -> int:
        with self._lock:
            return len(self._active_leases)

    def has_active_leases(self, extension_id: ExtensionId) -> bool:
        with self._lock:
            return self._extension_counts.get(extension_id, 0) > 0


default_lease_tracker = HandleLeaseTracker()
