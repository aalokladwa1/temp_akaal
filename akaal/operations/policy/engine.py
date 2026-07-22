"""
Operational Policy Engine.
Evaluates maintenance windows, escalation policies, and operational action restrictions.
"""

from typing import Dict, Any, List, Optional
from threading import RLock
import time


class OperationalPolicy:
    def __init__(self, policy_id: str, name: str, maintenance_windows_active: bool = False, require_approvals: bool = True) -> None:
        self.policy_id = policy_id
        self.name = name
        self.maintenance_windows_active = maintenance_windows_active
        self.require_approvals = require_approvals


class OperationsPolicyEngine:
    """Evaluates operations policies and maintenance window restrictions."""

    def __init__(self, default_policy: Optional[OperationalPolicy] = None) -> None:
        self._lock = RLock()
        self.active_policy = default_policy or OperationalPolicy("pol_default", "Default Operational Policy")

    def update_policy(self, policy: OperationalPolicy) -> None:
        with self._lock:
            self.active_policy = policy

    def is_action_permitted(self, action_name: str, session_active: bool = True) -> bool:
        with self._lock:
            # Emergency stop is always permitted
            if action_name == "emergency_stop":
                return True
            
            if self.active_policy.require_approvals and not session_active:
                return False
            
            return True
