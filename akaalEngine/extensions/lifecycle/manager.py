"""
akaalEngine.extensions.lifecycle.manager
========================================
Coordinates lifecycle state transitions, lease tracking, and event notifications.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Sequence

from akaalEngine.extensions.errors.taxonomy import LifecycleTransitionError
from akaalEngine.extensions.lifecycle.leases import HandleLeaseTracker, LeaseToken, default_lease_tracker
from akaalEngine.extensions.lifecycle.notifications import NotificationDispatcher, default_notification_dispatcher
from akaalEngine.extensions.lifecycle.transitions import LifecycleStateMachine
from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.events import ExtensionEvent, ExtensionEventType
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration, StrategyId
from akaalEngine.extensions.models.lifecycle import ExtensionLifecycleSnapshot, TransitionRecord


class LifecycleManager:
    """
    Manages runtime lifecycle states, active lease counts, and state transition histories.
    """

    def __init__(
        self,
        lease_tracker: Optional[HandleLeaseTracker] = None,
        notification_dispatcher: Optional[NotificationDispatcher] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._lease_tracker = lease_tracker or default_lease_tracker
        self._dispatcher = notification_dispatcher or default_notification_dispatcher
        self._states: Dict[ExtensionId, ExtensionLifecycleState] = {}
        self._history: Dict[ExtensionId, List[TransitionRecord]] = {}
        self._last_transition_times: Dict[ExtensionId, float] = {}
        self._last_transition_reasons: Dict[ExtensionId, str] = {}

    def get_state(self, extension_id: ExtensionId) -> ExtensionLifecycleState:
        with self._lock:
            return self._states.get(extension_id, ExtensionLifecycleState.DISCOVERED)

    def transition_state(
        self,
        extension_id: ExtensionId,
        new_state: ExtensionLifecycleState,
        generation: RegistryGeneration,
        reason: str,
        operator: Optional[str] = None,
    ) -> ExtensionLifecycleSnapshot:
        with self._lock:
            current_state = self.get_state(extension_id)
            LifecycleStateMachine.validate_transition(
                target_id=extension_id.value,
                current_state=current_state,
                new_state=new_state,
            )

            now = time.time()
            self._states[extension_id] = new_state
            self._last_transition_times[extension_id] = now
            self._last_transition_reasons[extension_id] = reason

            rec = TransitionRecord(
                extension_id=extension_id,
                from_state=current_state,
                to_state=new_state,
                generation=generation,
                reason=reason,
                timestamp=now,
                operator=operator,
            )
            if extension_id not in self._history:
                self._history[extension_id] = []
            self._history[extension_id].append(rec)

            active_count = self._lease_tracker.get_extension_active_count(extension_id)
            snapshot = ExtensionLifecycleSnapshot(
                extension_id=extension_id,
                current_state=new_state,
                generation=generation,
                active_handle_count=active_count,
                last_transition_at=now,
                last_transition_reason=reason,
            )

        # Emit typed notification
        evt_type = {
            ExtensionLifecycleState.ACTIVE: ExtensionEventType.EXTENSION_ACTIVATED,
            ExtensionLifecycleState.INACTIVE: ExtensionEventType.EXTENSION_DEACTIVATED,
            ExtensionLifecycleState.UNAVAILABLE: ExtensionEventType.EXTENSION_UNAVAILABLE,
            ExtensionLifecycleState.FAULTED: ExtensionEventType.EXTENSION_FAULTED,
            ExtensionLifecycleState.REMOVED: ExtensionEventType.EXTENSION_REMOVED,
            ExtensionLifecycleState.REGISTERED: ExtensionEventType.EXTENSION_REGISTERED,
        }.get(new_state, ExtensionEventType.EXTENSION_ACTIVATED)

        self._dispatcher.emit(
            ExtensionEvent(
                event_type=evt_type,
                extension_id=extension_id,
                generation=generation,
                details={"from_state": current_state.value, "to_state": new_state.value, "reason": reason},
            )
        )

        return snapshot

    def record_replacement(
        self,
        extension_id: ExtensionId,
        generation: RegistryGeneration,
        reason: str = "Extension updated/replaced in catalog",
    ) -> ExtensionLifecycleSnapshot:
        """
        Records an atomic in-place replacement of an existing extension,
        preserving its current lifecycle state and updating generation & timestamp.
        """
        with self._lock:
            current_state = self.get_state(extension_id)
            now = time.time()
            self._last_transition_times[extension_id] = now
            self._last_transition_reasons[extension_id] = reason

            rec = TransitionRecord(
                extension_id=extension_id,
                from_state=current_state,
                to_state=current_state,
                generation=generation,
                reason=reason,
                timestamp=now,
                operator=None,
            )
            if extension_id not in self._history:
                self._history[extension_id] = []
            self._history[extension_id].append(rec)

            active_count = self._lease_tracker.get_extension_active_count(extension_id)
            snapshot = ExtensionLifecycleSnapshot(
                extension_id=extension_id,
                current_state=current_state,
                generation=generation,
                active_handle_count=active_count,
                last_transition_at=now,
                last_transition_reason=reason,
            )

        self._dispatcher.emit(
            ExtensionEvent(
                event_type=ExtensionEventType.EXTENSION_REGISTERED,
                extension_id=extension_id,
                generation=generation,
                details={"from_state": current_state.value, "to_state": current_state.value, "reason": reason},
            )
        )

        return snapshot

    def get_snapshot(self, extension_id: ExtensionId, generation: RegistryGeneration) -> ExtensionLifecycleSnapshot:
        with self._lock:
            state = self.get_state(extension_id)
            active_count = self._lease_tracker.get_extension_active_count(extension_id)
            last_time = self._last_transition_times.get(extension_id, 0.0)
            last_reason = self._last_transition_reasons.get(extension_id, "Initial")
            return ExtensionLifecycleSnapshot(
                extension_id=extension_id,
                current_state=state,
                generation=generation,
                active_handle_count=active_count,
                last_transition_at=last_time,
                last_transition_reason=last_reason,
            )

    def get_history(self, extension_id: ExtensionId) -> Sequence[TransitionRecord]:
        with self._lock:
            return tuple(self._history.get(extension_id, []))


default_lifecycle_manager = LifecycleManager()
