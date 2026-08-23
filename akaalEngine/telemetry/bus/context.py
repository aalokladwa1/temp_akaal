"""
akaalEngine.telemetry.bus.context
==================================
CorrelationContext managing thread-local trace & correlation propagation across execution contexts.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
import uuid
from typing import Dict, Optional

_current_correlation_context: ContextVar[Optional["CorrelationContext"]] = ContextVar("correlation_context", default=None)


@dataclass(frozen=True)
class CorrelationContext:
    """
    Immutable trace & correlation context passed across execution steps.
    """
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    causation_id: Optional[str] = None
    migration_id: Optional[str] = None
    run_id: Optional[str] = None
    task_id: Optional[str] = None
    attempt_id: Optional[str] = None
    worker_id: Optional[str] = None
    node_id: Optional[str] = None

    @classmethod
    def get_current(cls) -> "CorrelationContext":
        ctx = _current_correlation_context.get()
        if ctx is None:
            ctx = CorrelationContext()
            _current_correlation_context.set(ctx)
        return ctx

    @classmethod
    def set_current(cls, ctx: "CorrelationContext") -> None:
        _current_correlation_context.set(ctx)

    def child_context(self, task_id: Optional[str] = None, attempt_id: Optional[str] = None) -> "CorrelationContext":
        return CorrelationContext(
            correlation_id=self.correlation_id,
            causation_id=uuid.uuid4().hex,
            migration_id=self.migration_id,
            run_id=self.run_id,
            task_id=task_id or self.task_id,
            attempt_id=attempt_id or self.attempt_id,
            worker_id=self.worker_id,
            node_id=self.node_id,
        )

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "migration_id": self.migration_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "worker_id": self.worker_id,
            "node_id": self.node_id,
        }
