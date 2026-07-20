"""Saga Compensation Stack managing LIFO compensation step execution."""

import threading
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Tuple
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class CompensationStep:
    """Immutable compensation step entry on the LIFO stack."""

    step_id: str
    compensation_action: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "step_id": self.step_id,
            "compensation_action": self.compensation_action,
            "parameters": dict(self.parameters),
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "compensation_action": self.compensation_action,
            "parameters": dict(self.parameters),
            "checksum": self.checksum,
        }


class CompensationStack:
    """Thread-safe LIFO compensation stack for Saga execution."""

    def __init__(self) -> None:
        self._stack: List[CompensationStep] = []
        self._lock = threading.Lock()

    def push(self, step: CompensationStep) -> None:
        with self._lock:
            self._stack.append(step)

    def pop(self) -> Optional[CompensationStep]:
        with self._lock:
            if not self._stack:
                return None
            return self._stack.pop()

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._stack) == 0

    def size(self) -> int:
        with self._lock:
            return len(self._stack)
