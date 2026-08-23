"""
akaalEngine.extensions.lifecycle
================================
State machine transitions, drain-safe handle lease tracking, event dispatching, and lifecycle management.
"""

from akaalEngine.extensions.lifecycle.transitions import LifecycleStateMachine
from akaalEngine.extensions.lifecycle.leases import (
    HandleLeaseTracker,
    LeaseToken,
    default_lease_tracker,
)
from akaalEngine.extensions.lifecycle.notifications import (
    ExtensionEventListener,
    NotificationDispatcher,
    default_notification_dispatcher,
)
from akaalEngine.extensions.lifecycle.manager import (
    LifecycleManager,
    default_lifecycle_manager,
)

__all__ = [
    "LifecycleStateMachine",
    "HandleLeaseTracker",
    "LeaseToken",
    "default_lease_tracker",
    "ExtensionEventListener",
    "NotificationDispatcher",
    "default_notification_dispatcher",
    "LifecycleManager",
    "default_lifecycle_manager",
]
