"""
Strongly typed identifiers for the Enterprise Orchestration Platform.
Prevents primitive obsession across domain models and workflow execution.
"""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class JobId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("JobId value must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "job") -> "JobId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WorkflowId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WorkflowId value must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "wf") -> "WorkflowId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SessionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("SessionId value must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "sess") -> "SessionId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ConfigurationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ConfigurationId value must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "cfg") -> "ConfigurationId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value
