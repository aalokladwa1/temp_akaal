"""HealingSession state manager."""

import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from akaal.healing.core.models import HealingResult, HealingStatus, HealingPlan


@dataclass
class HealingSession:
    """Tracks state and progress of an active repair session."""

    session_id: str = field(default_factory=lambda: f"hsess_{uuid.uuid4().hex[:8]}")
    validation_session_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    state: HealingStatus = HealingStatus.INITIALIZED
    active_plan: Optional[HealingPlan] = None
    results: Dict[str, HealingResult] = field(default_factory=dict)
    total_repairs_executed: int = 0
    emergency_stop_triggered: bool = False

    def start(self) -> None:
        """Start healing session."""
        self.state = HealingStatus.EXECUTING
        self.start_time = time.time()

    def record_result(self, domain_name: str, result: HealingResult) -> None:
        """Record domain repair result."""
        self.results[domain_name] = result
        self.total_repairs_executed += result.successful_actions

    def complete(self, success: bool = True) -> None:
        """Complete session."""
        self.end_time = time.time()
        self.state = HealingStatus.COMPLETED if success else HealingStatus.FAILED

    def trigger_emergency_stop() -> None:
        """Freeze execution immediately."""
        self.emergency_stop_triggered = True
        self.state = HealingStatus.FAILED
        self.end_time = time.time()
