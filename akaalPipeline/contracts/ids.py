"""akaalPipeline.contracts.ids
===========================
Strongly-typed identifier objects for pipeline domains.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("MigrationId cannot be empty")

    @classmethod
    def generate(cls) -> MigrationId:
        return cls(f"mig-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DefinitionRevisionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("DefinitionRevisionId cannot be empty")

    @classmethod
    def generate(cls) -> DefinitionRevisionId:
        return cls(f"rev-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PlanVersionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("PlanVersionId cannot be empty")

    @classmethod
    def generate(cls) -> PlanVersionId:
        return cls(f"pv-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExecutionPlanId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ExecutionPlanId cannot be empty")

    @classmethod
    def generate(cls) -> ExecutionPlanId:
        return cls(f"plan-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InitializationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("InitializationId cannot be empty")

    @classmethod
    def generate(cls) -> InitializationId:
        return cls(f"init-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AttemptId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("AttemptId cannot be empty")

    @classmethod
    def generate(cls) -> AttemptId:
        return cls(f"att-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OperationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("OperationId cannot be empty")

    @classmethod
    def generate(cls) -> OperationId:
        return cls(f"op-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InvocationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("InvocationId cannot be empty")

    @classmethod
    def generate(cls) -> InvocationId:
        return cls(f"inv-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CheckpointId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("CheckpointId cannot be empty")

    @classmethod
    def generate(cls) -> CheckpointId:
        return cls(f"chk-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ScheduleId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ScheduleId cannot be empty")

    @classmethod
    def generate(cls) -> ScheduleId:
        return cls(f"sch-{uuid.uuid4().hex}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TenantId:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WorkspaceId:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProjectId:
    value: str

    def __str__(self) -> str:
        return self.value
