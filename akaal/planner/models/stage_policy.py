"""
Akaal — Stage Policy Model
==========================
Embedded stage policies defining retry, checkpoint, failure, validation, and rollback rules per ExecutionStage.
Planner defines these policies statically without executing them.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class StagePolicy:
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 5.0
    checkpoint_enabled: bool = True
    on_failure_action: str = "TRIGGER_ROLLBACK"  # "CONTINUE", "PAUSE", "TRIGGER_ROLLBACK"
    validation_gate_required: bool = True
    rollback_policy: str = "AUTOMATIC_COMPENSATION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retry_max_attempts": self.retry_max_attempts,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "checkpoint_enabled": self.checkpoint_enabled,
            "on_failure_action": self.on_failure_action,
            "validation_gate_required": self.validation_gate_required,
            "rollback_policy": self.rollback_policy,
        }
