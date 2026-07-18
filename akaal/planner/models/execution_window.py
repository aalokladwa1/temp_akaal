"""
Akaal — Execution Window Model
==============================
First-class planning models defining time windows for maintenance, cutover, and rollback.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class WindowType(str, Enum):
    MAINTENANCE = "MAINTENANCE"
    BUSINESS = "BUSINESS"
    FREEZE = "FREEZE"
    CUTOVER = "CUTOVER"
    VALIDATION = "VALIDATION"
    ROLLBACK = "ROLLBACK"


@dataclass
class ExecutionWindow:
    window_id: str
    window_type: WindowType
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    max_allowed_duration_minutes: float = 60.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "window_type": self.window_type.value if hasattr(self.window_type, "value") else str(self.window_type),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "max_allowed_duration_minutes": self.max_allowed_duration_minutes,
            "attributes": self.attributes,
        }
