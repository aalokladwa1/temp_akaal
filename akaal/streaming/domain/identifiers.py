"""
Strongly typed identifiers for Platform 3 - Streaming Execution Engine.
"""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class StreamId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("StreamId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "stream") -> "StreamId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OperatorId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("OperatorId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "op") -> "OperatorId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class BatchId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("BatchId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "batch") -> "BatchId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WatermarkId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WatermarkId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "wm") -> "WatermarkId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WindowId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("WindowId must be a non-empty string.")

    @classmethod
    def generate(cls, prefix: str = "win") -> "WindowId":
        return cls(value=f"{prefix}_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value
