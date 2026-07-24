"""RepairAuditTrailService: Maintains complete audit history (Who, What, When, Why, Result) (Cap 22)."""

import time
from typing import List, Dict, Any
from akaal.healing.core.interfaces import IHealingService


class RepairAuditTrailService(IHealingService):
    """Infrastructure service tracking audit history for governance and compliance."""

    @property
    def service_name(self) -> str:
        return "RepairAuditTrailService"

    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []

    def log_repair_entry(self, session_id: str, action_name: str, status: str, user_id: str = "SYSTEM") -> None:
        """Log repair audit entry."""
        self._audit_log.append({
            "timestamp": time.time(),
            "session_id": session_id,
            "action_name": action_name,
            "status": status,
            "user_id": user_id,
        })

    def get_audit_trail(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit log for session."""
        return [entry for entry in self._audit_log if entry["session_id"] == session_id]
