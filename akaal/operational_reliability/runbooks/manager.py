"""
AKAAL Platform 7 — Runbook & Operational Playbook Manager.
"""

from typing import Dict, Optional, List
import uuid
from akaal.operational_reliability.domain.models import OperationalRunbook


class RunbookManager:
    """Maintains operational runbooks, playbooks, and incident response procedures."""

    def __init__(self) -> None:
        self._runbooks: Dict[str, OperationalRunbook] = {}

    def create_runbook(self, title: str, service_id: str, trigger_conditions: List[str], steps: List[str], author: str) -> OperationalRunbook:
        rb_id = f"rb-{uuid.uuid4().hex[:8]}"
        runbook = OperationalRunbook(
            runbook_id=rb_id,
            title=title,
            service_id=service_id,
            trigger_conditions=trigger_conditions,
            steps=steps,
            author=author,
        )
        self._runbooks[rb_id] = runbook
        return runbook

    def get_runbook_for_service(self, service_id: str) -> Optional[OperationalRunbook]:
        for rb in self._runbooks.values():
            if rb.service_id == service_id:
                return rb
        return None
