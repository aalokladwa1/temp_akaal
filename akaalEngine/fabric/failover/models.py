"""
akaalEngine.fabric.failover.models
======================================
P7B.28 -- Disaster Recovery & Geo Failover data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from akaalEngine.fabric.ownership.models import OwnershipRecord
from akaalEngine.fabric.placement.engine import PlacementEvaluationResult


class FailoverOutcome(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    NO_COMPLIANT_CANDIDATE = "NO_COMPLIANT_CANDIDATE"
    SUCCEEDED = "SUCCEEDED"


@dataclass(frozen=True)
class FailoverResult:
    outcome: FailoverOutcome
    old_ownership_key: str
    old_record: Optional[OwnershipRecord]
    new_record: Optional[OwnershipRecord]
    selected_site_id: Optional[str]
    placement_result: Optional[PlacementEvaluationResult]
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    def succeeded(self) -> bool:
        return self.outcome == FailoverOutcome.SUCCEEDED
