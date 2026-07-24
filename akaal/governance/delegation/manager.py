"""
AKAAL Platform 6 — Delegated Approvals Manager.
"""

from typing import Dict, List, Optional
import datetime
import uuid


class DelegationManager:
    """Manages temporary approval delegation with time limits and validation."""

    def __init__(self) -> None:
        self._delegations: Dict[str, Dict[str, Any]] = {}

    def delegate_approval(self, delegator_id: str, delegatee_id: str, duration_hours: int = 48) -> Dict[str, Any]:
        delegation_id = f"dlg-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = (now + datetime.timedelta(hours=duration_hours)).isoformat()

        delegation = {
            "delegation_id": delegation_id,
            "delegator_id": delegator_id,
            "delegatee_id": delegatee_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "is_active": True,
        }
        self._delegations[delegation_id] = delegation
        return delegation

    def resolve_effective_approver(self, approver_id: str) -> str:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for d in self._delegations.values():
            if d["delegator_id"] == approver_id and d["is_active"] and d["expires_at"] > now:
                return d["delegatee_id"]
        return approver_id
