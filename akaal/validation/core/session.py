"""ValidationSession state manager."""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from akaal.validation.core.models import ValidationResult, ValidationStatus


class SessionState(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ValidationSession:
    """Tracks state and progress of an active validation run."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_uri: str = ""
    target_uri: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    state: SessionState = SessionState.INITIALIZED
    results: Dict[str, ValidationResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_checks_executed: int = 0
    total_issues_found: int = 0

    def start(self) -> None:
        """Mark session as running."""
        self.state = SessionState.RUNNING
        self.start_time = time.time()

    def record_result(self, domain_name: str, result: ValidationResult) -> None:
        """Record validation result from a domain validator."""
        self.results[domain_name] = result
        self.total_checks_executed += len(result.capabilities_tested)
        self.total_issues_found += len(result.issues)

    def complete(self, success: bool = True) -> None:
        """Mark session as completed or failed."""
        self.end_time = time.time()
        self.state = SessionState.COMPLETED if success else SessionState.FAILED

    @property
    def duration_seconds(self) -> float:
        """Return overall execution duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
