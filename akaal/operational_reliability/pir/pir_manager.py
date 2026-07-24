"""
AKAAL Platform 7 — Post-Incident Review (PIR) & Action Item Tracker.
"""

from typing import Dict, List, Optional
import datetime
import uuid
from akaal.operational_reliability.domain.models import PostIncidentReview


class PostIncidentReviewManager:
    """Manages Root Cause Analysis (RCA), corrective actions, preventive actions, and PIR history."""

    def __init__(self) -> None:
        self._pirs: Dict[str, PostIncidentReview] = {}

    def create_pir(
        self,
        incident_id: str,
        root_cause_analysis: str,
        contributing_factors: List[str],
        corrective_actions: List[str],
        preventive_actions: List[str],
        lessons_learned: List[str],
    ) -> PostIncidentReview:
        pir_id = f"pir-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        pir = PostIncidentReview(
            pir_id=pir_id,
            incident_id=incident_id,
            root_cause_analysis=root_cause_analysis,
            contributing_factors=contributing_factors,
            corrective_actions=corrective_actions,
            preventive_actions=preventive_actions,
            lessons_learned=lessons_learned,
            completed_at=now,
        )
        self._pirs[pir_id] = pir
        return pir

    def get_pir_for_incident(self, incident_id: str) -> Optional[PostIncidentReview]:
        for p in self._pirs.values():
            if p.incident_id == incident_id:
                return p
        return None
