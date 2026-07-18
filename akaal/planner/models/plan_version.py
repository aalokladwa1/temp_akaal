"""
Akaal — Plan Versioning Model
=============================
Immutable version tracking model for MigrationExecutionPlan revisions.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PlanVersionInfo:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_plan_id: Optional[str] = None
    revision: int = 1
    revision_history: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "parent_plan_id": self.parent_plan_id,
            "revision": self.revision,
            "revision_history": self.revision_history,
            "timestamp": self.timestamp,
        }
