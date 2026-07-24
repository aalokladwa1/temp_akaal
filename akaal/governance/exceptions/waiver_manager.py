"""
AKAAL Platform 6 — Exception & Waiver Management.
"""

from typing import Dict, Optional, List
import datetime
import uuid

from akaal.governance.domain.models import ExceptionWaiver


class ExceptionWaiverManager:
    """Manages governance exceptions, policy waivers, and expiration tracking."""

    def __init__(self) -> None:
        self._waivers: Dict[str, ExceptionWaiver] = {}

    def grant_waiver(
        self,
        policy_id: str,
        requested_by: str,
        justification: str,
        duration_hours: int = 72,
        approved_by: Optional[str] = None,
    ) -> ExceptionWaiver:
        waiver_id = f"wvr-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = (now + datetime.timedelta(hours=duration_hours)).isoformat()

        waiver = ExceptionWaiver(
            waiver_id=waiver_id,
            policy_id=policy_id,
            requested_by=requested_by,
            approved_by=approved_by,
            justification=justification,
            granted_at=now.isoformat(),
            expires_at=expires_at,
            is_active=True,
        )
        self._waivers[waiver_id] = waiver
        return waiver

    def has_active_waiver(self, policy_id: str) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for w in self._waivers.values():
            if w.policy_id == policy_id and w.is_active and w.expires_at > now:
                return True
        return False

    def list_active_waivers(self) -> List[ExceptionWaiver]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return [w for w in self._waivers.values() if w.is_active and w.expires_at > now]
