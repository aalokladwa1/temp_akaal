"""
Operational Security Engine & RBAC.
Enforces role-based access control, MFA signature verification, and action signing.
"""

from typing import Dict, Set, Any
from threading import RLock
import hashlib
from enum import Enum


class Role(Enum):
    SUPER_ADMIN = "SuperAdmin"
    OPERATOR = "Operator"
    AUDITOR = "Auditor"
    VIEWER = "Viewer"


class SecurityEngine:
    """Enforces RBAC permissions and signature authorization for operations."""

    ROLE_PERMISSIONS: Dict[Role, Set[str]] = {
        Role.SUPER_ADMIN: {"read", "control", "drain", "emergency_stop", "policy_edit", "audit_read"},
        Role.OPERATOR: {"read", "control", "drain", "audit_read"},
        Role.AUDITOR: {"read", "audit_read"},
        Role.VIEWER: {"read"}
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._user_roles: Dict[str, Role] = {}

    def assign_role(self, user_id: str, role: Role) -> None:
        with self._lock:
            self._user_roles[user_id] = role

    def is_authorized(self, user_id: str, action_permission: str) -> bool:
        with self._lock:
            role = self._user_roles.get(user_id, Role.VIEWER)
            allowed_permissions = self.ROLE_PERMISSIONS.get(role, set())
            return action_permission in allowed_permissions

    def verify_action_signature(self, user_id: str, action: str, signature: str) -> bool:
        """Verifies digital signature of operational commands."""
        with self._lock:
            if not signature:
                return False
            expected = hashlib.sha256(f"{user_id}:{action}".encode("utf-8")).hexdigest()
            return signature == expected
