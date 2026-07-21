"""
Strongly typed identifiers for Enterprise Distributed Runtime (Platform 2).
Prevents primitive obsession across distributed models and coordination interfaces.
"""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class WorkerId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WorkerId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "worker") -> "WorkerId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class NodeId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("NodeId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "node") -> "NodeId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ClusterId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ClusterId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "cluster") -> "ClusterId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaskId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("TaskId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "task") -> "TaskId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExecutionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ExecutionId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "exec") -> "ExecutionId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AttemptId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("AttemptId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "att") -> "AttemptId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LeaseId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("LeaseId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "lease") -> "LeaseId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CorrelationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("CorrelationId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "corr") -> "CorrelationId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ReservationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ReservationId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "resv") -> "ReservationId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class IdempotencyKey:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("IdempotencyKey must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "idempotency") -> "IdempotencyKey":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value
