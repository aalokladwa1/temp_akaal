"""
AKAAL Platform 6 — Emergency Override Workflow Service.
"""

from typing import Dict, Optional
import datetime
import uuid

from akaal.governance.domain.models import EmergencyOverride
from akaal.governance.domain.enums import EmergencyReason


class EmergencyOverrideService:
    """Manages controlled break-glass emergency override workflows with mandatory audit trails."""

    def __init__(self) -> None:
        self._overrides: Dict[str, EmergencyOverride] = {}

    def trigger_override(
        self,
        operation_id: str,
        justification: str,
        reason_category: EmergencyReason,
        authorized_by: str,
        duration_minutes: int = 60,
    ) -> EmergencyOverride:
        override_id = f"ovr-{uuid.uuid4().hex[:8]}"
        valid_until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration_minutes)).isoformat()

        override = EmergencyOverride(
            override_id=override_id,
            operation_id=operation_id,
            justification=justification,
            reason_category=reason_category,
            authorized_by=authorized_by,
            valid_until=valid_until,
            is_active=True,
        )
        self._overrides[override_id] = override
        return override

    def is_override_active(self, override_id: str) -> bool:
        ovr = self._overrides.get(override_id)
        if not ovr or not ovr.is_active:
            return False
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return ovr.valid_until > now

    def revoke_override(self, override_id: str) -> bool:
        ovr = self._overrides.get(override_id)
        if ovr:
            updated = EmergencyOverride(
                override_id=ovr.override_id,
                operation_id=ovr.operation_id,
                justification=ovr.justification,
                reason_category=ovr.reason_category,
                authorized_by=ovr.authorized_by,
                valid_until=ovr.valid_until,
                is_active=False,
            )
            self._overrides[override_id] = updated
            return True
        return False
