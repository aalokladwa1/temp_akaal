"""
AKAAL Platform 6 — Governance Audit Trail Generator.
"""

from typing import List, Dict, Any, Optional
import datetime
import uuid


class GovernanceAuditTrailService:
    """Generates immutable governance audit trail entries."""

    def __init__(self) -> None:
        self._audit_records: List[Dict[str, Any]] = []

    def record_audit(
        self,
        who: str,
        what: str,
        why: str,
        target: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        decision: str,
    ) -> Dict[str, Any]:
        record_id = f"audit-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry = {
            "record_id": record_id,
            "timestamp": now,
            "who": who,
            "what": what,
            "why": why,
            "target": target,
            "before_state": before_state,
            "after_state": after_state,
            "decision": decision,
        }
        self._audit_records.append(entry)
        return entry

    def get_audit_trail(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        if target:
            return [r for r in self._audit_records if r["target"] == target]
        return list(self._audit_records)
